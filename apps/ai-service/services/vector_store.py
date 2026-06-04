"""
Qdrant vector store service.

Collections:
  - jobs     : 1 vector per job  (embedding_dim dimensions)
  - profiles : 1 vector per user (embedding_dim dimensions)

Used for:
  - ANN job feed ranking (replaces brute-force cosine_similarity over all jobs)
  - Semantic search ("find jobs similar to this job")
  - Profile → job matching at scale
"""
from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from config import settings

if TYPE_CHECKING:
    from models.job import Job
    from models.user import UserProfile

log = logging.getLogger(__name__)

JOBS_COLLECTION     = "jobs"
PROFILES_COLLECTION = "profiles"
DIM = settings.embedding_dim  # 384 for all-MiniLM, 1536 for OpenAI ada-002


# ─── Client singleton ─────────────────────────────────────────────────────────

_client: AsyncQdrantClient | None = None


def get_qdrant() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=30,
        )
    return _client


# ─── Collection initialisation ────────────────────────────────────────────────

async def ensure_collections() -> None:
    """Create Qdrant collections if they don't exist. Call on startup."""
    client = get_qdrant()
    existing = {c.name for c in (await client.get_collections()).collections}

    for name in (JOBS_COLLECTION, PROFILES_COLLECTION):
        if name not in existing:
            await client.create_collection(
                collection_name=name,
                vectors_config=qmodels.VectorParams(
                    size=DIM,
                    distance=qmodels.Distance.COSINE,
                ),
                optimizers_config=qmodels.OptimizersConfigDiff(
                    indexing_threshold=10_000,  # build HNSW after 10k points
                ),
                hnsw_config=qmodels.HnswConfigDiff(
                    m=16,
                    ef_construct=200,
                    full_scan_threshold=10_000,
                ),
            )
            log.info("Created Qdrant collection: %s", name)


# ─── Job vector operations ────────────────────────────────────────────────────

async def upsert_job(job: "Job", embedding: list[float]) -> None:
    """Store or update a job's embedding in Qdrant."""
    client = get_qdrant()
    await client.upsert(
        collection_name=JOBS_COLLECTION,
        points=[
            qmodels.PointStruct(
                id=str(job.id),
                vector=embedding,
                payload={
                    "title":          job.title,
                    "company":        job.company,
                    "location":       job.location,
                    "is_remote":      job.is_remote,
                    "job_type":       job.job_type,
                    "industry":       job.industry,
                    "skills":         job.skills_required or [],
                    "experience_min": float(job.experience_min or 0),
                    "experience_max": float(job.experience_max or 50),
                    "salary_min":     float(job.salary_min_lpa or 0),
                    "salary_max":     float(job.salary_max_lpa or 0),
                    "source":         job.source,
                    "is_active":      job.is_active,
                },
            )
        ],
    )


async def delete_job(job_id: str) -> None:
    client = get_qdrant()
    await client.delete(
        collection_name=JOBS_COLLECTION,
        points_selector=qmodels.PointIdsList(points=[job_id]),
    )


async def search_similar_jobs(
    query_embedding: list[float],
    limit: int = 50,
    score_threshold: float = 0.55,
    filters: dict | None = None,
) -> list[tuple[str, float]]:
    """
    ANN search — returns list of (job_id, cosine_score) sorted by score desc.
    Applies optional Qdrant payload filters (e.g. location, job_type).
    """
    client = get_qdrant()

    qdrant_filter = None
    if filters:
        must_conditions = []
        if filters.get("is_remote") is True:
            must_conditions.append(
                qmodels.FieldCondition(key="is_remote", match=qmodels.MatchValue(value=True))
            )
        if filters.get("job_type"):
            must_conditions.append(
                qmodels.FieldCondition(key="job_type", match=qmodels.MatchValue(value=filters["job_type"]))
            )
        if filters.get("location"):
            must_conditions.append(
                qmodels.FieldCondition(key="location", match=qmodels.MatchText(text=filters["location"]))
            )
        if must_conditions:
            qdrant_filter = qmodels.Filter(must=must_conditions)

    # Always filter to active jobs only
    active_filter = qmodels.FieldCondition(key="is_active", match=qmodels.MatchValue(value=True))
    if qdrant_filter:
        qdrant_filter.must = (qdrant_filter.must or []) + [active_filter]
    else:
        qdrant_filter = qmodels.Filter(must=[active_filter])

    results = await client.search(
        collection_name=JOBS_COLLECTION,
        query_vector=query_embedding,
        limit=limit,
        score_threshold=score_threshold,
        query_filter=qdrant_filter,
        with_payload=False,  # we only need IDs + scores
    )

    return [(str(r.id), r.score) for r in results]


# ─── Profile vector operations ────────────────────────────────────────────────

async def upsert_profile(profile: "UserProfile", embedding: list[float]) -> None:
    client = get_qdrant()
    await client.upsert(
        collection_name=PROFILES_COLLECTION,
        points=[
            qmodels.PointStruct(
                id=str(profile.user_id),
                vector=embedding,
                payload={
                    "skills":       profile.skills or [],
                    "exp_years":    float(profile.experience_years or 0),
                    "locations":    profile.preferred_locations or [],
                    "job_types":    profile.job_types or [],
                },
            )
        ],
    )


async def get_job_ids_by_vector(
    profile_embedding: list[float],
    limit: int = 100,
    exclude_ids: list[str] | None = None,
) -> list[tuple[str, float]]:
    """High-level helper: find top jobs for a profile, excluding already-swiped IDs."""
    filters: dict = {}
    results = await search_similar_jobs(profile_embedding, limit=limit + len(exclude_ids or []), filters=filters)

    exclude_set = set(exclude_ids or [])
    return [(job_id, score) for job_id, score in results if job_id not in exclude_set][:limit]


# ─── Bulk indexing (for seed / scraper pipeline) ─────────────────────────────

async def bulk_upsert_jobs(jobs_with_embeddings: list[tuple["Job", list[float]]]) -> int:
    """Upsert a batch of jobs into Qdrant. Returns count upserted."""
    client = get_qdrant()
    if not jobs_with_embeddings:
        return 0

    points = [
        qmodels.PointStruct(
            id=str(job.id),
            vector=embedding,
            payload={
                "title":          job.title,
                "company":        job.company,
                "location":       job.location or "",
                "is_remote":      job.is_remote,
                "job_type":       job.job_type or "",
                "industry":       job.industry or "",
                "skills":         job.skills_required or [],
                "experience_min": float(job.experience_min or 0),
                "experience_max": float(job.experience_max or 50),
                "salary_min":     float(job.salary_min_lpa or 0),
                "salary_max":     float(job.salary_max_lpa or 0),
                "source":         job.source,
                "is_active":      job.is_active,
            },
        )
        for job, embedding in jobs_with_embeddings
    ]

    # Qdrant recommends batches of ≤100
    BATCH = 100
    for i in range(0, len(points), BATCH):
        await client.upsert(collection_name=JOBS_COLLECTION, points=points[i: i + BATCH])

    log.info("Bulk upserted %d jobs into Qdrant", len(points))
    return len(points)
