"""
Meilisearch service — full-text job search.

Index: "jobs"
  - Searchable: title, company, location, description, skills_required, industry
  - Filterable: job_type, is_remote, source, is_active
  - Sortable: posted_at, salary_max_lpa
  - Ranking: typo, words, proximity, attribute, exactness

Usage:
  await search_jobs("python developer bangalore", filters={"is_remote": True})
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from config import settings

log = logging.getLogger(__name__)

MEILI_URL   = settings.meilisearch_url
MEILI_KEY   = settings.meilisearch_master_key
INDEX_NAME  = "jobs"
HEADERS     = {"Authorization": f"Bearer {MEILI_KEY}", "Content-Type": "application/json"}

# ─── Index setup ─────────────────────────────────────────────────────────────

async def ensure_index() -> None:
    """Create index and configure settings. Safe to call on every startup."""
    async with httpx.AsyncClient(base_url=MEILI_URL, headers=HEADERS) as client:
        # Create index if missing
        try:
            await client.post("/indexes", json={"uid": INDEX_NAME, "primaryKey": "id"})
        except Exception:
            pass  # already exists

        # Configure index settings
        await client.patch(
            f"/indexes/{INDEX_NAME}/settings",
            json={
                "searchableAttributes": [
                    "title", "company", "location", "skills_required",
                    "description", "industry", "job_type",
                ],
                "filterableAttributes": [
                    "job_type", "is_remote", "source", "is_active",
                    "industry", "location",
                ],
                "sortableAttributes": [
                    "posted_at", "salary_max_lpa", "salary_min_lpa",
                ],
                "rankingRules": [
                    "words", "typo", "proximity", "attribute", "sort", "exactness",
                ],
                "typoTolerance": {
                    "enabled": True,
                    "minWordSizeForTypos": {"oneTypo": 4, "twoTypos": 8},
                },
            },
        )
        log.info("Meilisearch index '%s' configured", INDEX_NAME)


# ─── Indexing ─────────────────────────────────────────────────────────────────

async def index_job(job_doc: dict) -> None:
    """Add or update a single job document in Meilisearch."""
    async with httpx.AsyncClient(base_url=MEILI_URL, headers=HEADERS, timeout=10) as client:
        await client.post(f"/indexes/{INDEX_NAME}/documents", json=[job_doc])


async def bulk_index_jobs(job_docs: list[dict]) -> None:
    """Bulk upsert up to 1000 job documents."""
    if not job_docs:
        return
    BATCH = 500
    async with httpx.AsyncClient(base_url=MEILI_URL, headers=HEADERS, timeout=30) as client:
        for i in range(0, len(job_docs), BATCH):
            await client.post(f"/indexes/{INDEX_NAME}/documents", json=job_docs[i: i + BATCH])
    log.info("Indexed %d jobs in Meilisearch", len(job_docs))


async def delete_job(job_id: str) -> None:
    async with httpx.AsyncClient(base_url=MEILI_URL, headers=HEADERS, timeout=10) as client:
        await client.delete(f"/indexes/{INDEX_NAME}/documents/{job_id}")


# ─── Search ───────────────────────────────────────────────────────────────────

async def search_jobs(
    query: str,
    limit: int = 20,
    offset: int = 0,
    filters: dict | None = None,
    sort: list[str] | None = None,
) -> dict[str, Any]:
    """
    Full-text search. Returns Meilisearch response dict with:
      hits, estimatedTotalHits, limit, offset, processingTimeMs
    """
    filter_parts: list[str] = ["is_active = true"]

    if filters:
        if filters.get("is_remote") is True:
            filter_parts.append("is_remote = true")
        if filters.get("job_type"):
            filter_parts.append(f"job_type = '{filters['job_type']}'")
        if filters.get("location"):
            filter_parts.append(f"location = '{filters['location']}'")
        if filters.get("industry"):
            filter_parts.append(f"industry = '{filters['industry']}'")

    body: dict[str, Any] = {
        "q":                query,
        "limit":            limit,
        "offset":           offset,
        "filter":           " AND ".join(filter_parts),
        "attributesToHighlight": ["title", "company", "skills_required"],
        "highlightPreTag":  "<mark>",
        "highlightPostTag": "</mark>",
    }
    if sort:
        body["sort"] = sort

    async with httpx.AsyncClient(base_url=MEILI_URL, headers=HEADERS, timeout=10) as client:
        resp = await client.post(f"/indexes/{INDEX_NAME}/search", json=body)
        resp.raise_for_status()
        return resp.json()


# ─── Document builder ─────────────────────────────────────────────────────────

def job_to_document(job: Any) -> dict:
    """Convert a SQLAlchemy Job model instance to a Meilisearch document."""
    return {
        "id":              str(job.id),
        "title":           job.title,
        "company":         job.company,
        "company_logo":    job.company_logo,
        "location":        job.location or "",
        "is_remote":       job.is_remote,
        "salary_min_lpa":  float(job.salary_min_lpa or 0),
        "salary_max_lpa":  float(job.salary_max_lpa or 0),
        "experience_min":  float(job.experience_min or 0),
        "experience_max":  float(job.experience_max or 50),
        "skills_required": job.skills_required or [],
        "description":     (job.description or "")[:500],
        "apply_url":       job.apply_url or "",
        "job_type":        job.job_type or "",
        "industry":        job.industry or "",
        "source":          job.source,
        "is_active":       job.is_active,
        "posted_at":       job.posted_at.isoformat() if job.posted_at else "",
    }
