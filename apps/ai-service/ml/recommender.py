"""
Recommendation engine — ranks jobs for a user using:
1. Qdrant ANN search (fast cosine similarity on embeddings) — primary path
2. Fallback: brute-force sklearn cosine_similarity if Qdrant unavailable
3. Composite match score (skills, experience, location, salary, semantic)
4. Exclusion of already-swiped jobs
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine

from ml.embeddings import embed_profile, embed_job
from ml.scorer import compute_match_score, ScoreDetails

if TYPE_CHECKING:
    from models.user import UserProfile
    from models.job import Job

log = logging.getLogger(__name__)


async def rank_jobs_for_user(
    profile: "UserProfile",
    jobs: list["Job"],
    swiped_job_ids: set[str],
    use_qdrant: bool = True,
) -> list[tuple["Job", ScoreDetails]]:
    """
    Returns (job, score_details) sorted by total score desc.
    Filters out already-swiped jobs.

    Strategy:
      1. Get user profile embedding
      2. Query Qdrant for top-N nearest job IDs + cosine scores (fast ANN)
      3. Fetch those jobs from the provided `jobs` list
      4. Apply composite scorer
      5. Fallback to brute-force if Qdrant unavailable or jobs list is small
    """
    if not jobs:
        return []

    user_embedding = await embed_profile(profile)

    # ─── Try Qdrant ANN path ──────────────────────────────────────────────────
    if use_qdrant:
        try:
            from services.vector_store import get_job_ids_by_vector

            qdrant_results = await get_job_ids_by_vector(
                profile_embedding=user_embedding,
                limit=min(len(jobs) + len(swiped_job_ids), 300),
                exclude_ids=list(swiped_job_ids),
            )
            # Build score lookup: job_id → cosine_score
            cosine_map: dict[str, float] = {jid: score for jid, score in qdrant_results}

            # Build job lookup
            job_map = {str(j.id): j for j in jobs}

            results: list[tuple["Job", ScoreDetails]] = []
            for job_id, cos_sim in qdrant_results:
                job = job_map.get(job_id)
                if job and str(job.id) not in swiped_job_ids:
                    details = compute_match_score(profile, job, cos_sim)
                    results.append((job, details))

            if results:
                results.sort(key=lambda x: (x[1].total, x[0].posted_at), reverse=True)
                log.debug("Qdrant ANN returned %d ranked jobs", len(results))
                return results

        except Exception as e:
            log.warning("Qdrant unavailable, falling back to brute-force: %s", e)

    # ─── Brute-force fallback ─────────────────────────────────────────────────
    return await _brute_force_rank(profile, user_embedding, jobs, swiped_job_ids)


async def _brute_force_rank(
    profile: "UserProfile",
    user_embedding: list[float],
    jobs: list["Job"],
    swiped_job_ids: set[str],
) -> list[tuple["Job", ScoreDetails]]:
    """sklearn cosine similarity over all provided jobs. Used as Qdrant fallback."""
    user_vec = np.array(user_embedding).reshape(1, -1)

    # Embed all jobs in parallel
    job_embeddings = await asyncio.gather(*[embed_job(j) for j in jobs])
    job_matrix = np.array(job_embeddings)
    cosine_scores = sklearn_cosine(user_vec, job_matrix)[0]

    results: list[tuple["Job", ScoreDetails]] = []
    for job, cos_sim in zip(jobs, cosine_scores):
        if str(job.id) in swiped_job_ids:
            continue
        details = compute_match_score(profile, job, float(cos_sim))
        results.append((job, details))

    results.sort(key=lambda x: (x[1].total, x[0].posted_at), reverse=True)
    return results


def filter_by_preferences(
    jobs: list["Job"],
    profile: "UserProfile",
) -> list["Job"]:
    """
    Hard-filter pass before ML ranking — removes jobs that definitively
    don't match user's hard constraints (saves compute on ranking).
    """
    filtered = []
    for job in jobs:
        # Skip severely underqualified (>2 years gap)
        if profile.experience_years and job.experience_min:
            if float(profile.experience_years) < float(job.experience_min) - 2:
                continue
        # Skip if job type preference set and this job doesn't match
        if profile.job_types and job.job_type:
            if job.job_type not in profile.job_types:
                continue
        filtered.append(job)
    return filtered
