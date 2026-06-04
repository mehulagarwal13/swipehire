"""
ML scoring tasks — recompute match scores for all active users nightly.
Also triggered on-demand when a new job batch is scraped.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import settings
from models.job import Job
from models.user import User, UserProfile
from workers.celery_app import app

log = logging.getLogger(__name__)


def _make_session():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False), engine


@app.task(
    queue="ml",
    name="workers.scoring_tasks.recompute_all_match_scores",
    time_limit=3600,      # 1 hour max
    soft_time_limit=3300,
)
def recompute_all_match_scores() -> dict:
    return asyncio.get_event_loop().run_until_complete(_recompute_all_async())


async def _recompute_all_async() -> dict:
    from ml.embeddings import embed_profile
    from ml.scorer import compute_match_score
    from services.vector_store import get_job_ids_by_vector

    session_factory, engine = _make_session()
    total_scores = 0

    async with session_factory() as db:
        # Get all onboarded users
        users_result = await db.execute(
            select(User, UserProfile)
            .join(UserProfile, UserProfile.user_id == User.id)
            .where(UserProfile.is_onboarded == True, User.is_active == True)
        )
        user_pairs = users_result.all()

        # Get all active jobs
        jobs_result = await db.execute(
            select(Job).where(Job.is_active == True)
        )
        all_jobs = jobs_result.scalars().all()
        job_map = {str(j.id): j for j in all_jobs}

        log.info("Recomputing scores: %d users × %d jobs", len(user_pairs), len(all_jobs))

        for user, profile in user_pairs:
            try:
                user_embedding = await embed_profile(profile)

                # Get top-200 jobs from Qdrant ANN
                top_job_ids = await get_job_ids_by_vector(
                    profile_embedding=user_embedding,
                    limit=200,
                )

                # Score each matched job
                for job_id, cosine_sim in top_job_ids:
                    job = job_map.get(job_id)
                    if not job:
                        continue

                    details = compute_match_score(profile, job, cosine_sim)

                    # Upsert into job_match_scores
                    await db.execute(
                        text("""
                            INSERT INTO job_match_scores (user_id, job_id, score, score_details, computed_at)
                            VALUES (:user_id, :job_id, :score, :details::jsonb, NOW())
                            ON CONFLICT (user_id, job_id)
                            DO UPDATE SET
                                score = EXCLUDED.score,
                                score_details = EXCLUDED.score_details,
                                computed_at = NOW()
                        """),
                        {
                            "user_id": str(user.id),
                            "job_id":  job_id,
                            "score":   details.total,
                            "details": str(details.to_dict()).replace("'", '"'),
                        },
                    )
                    total_scores += 1

                await db.commit()

            except Exception as e:
                log.error("Score computation failed for user %s: %s", user.id, e)
                continue

    await engine.dispose()
    log.info("Recomputed %d match scores", total_scores)
    return {"scores_computed": total_scores}


@app.task(
    queue="ml",
    name="workers.scoring_tasks.score_jobs_for_user",
)
def score_jobs_for_user(user_id: str) -> dict:
    """On-demand: recompute scores for a single user (e.g. after profile update)."""
    return asyncio.get_event_loop().run_until_complete(_score_user_async(user_id))


async def _score_user_async(user_id: str) -> dict:
    from ml.embeddings import embed_profile
    from ml.scorer import compute_match_score
    from services.vector_store import get_job_ids_by_vector

    session_factory, engine = _make_session()
    scored = 0

    async with session_factory() as db:
        result = await db.execute(
            select(User, UserProfile)
            .join(UserProfile, UserProfile.user_id == User.id)
            .where(User.id == user_id)
        )
        row = result.one_or_none()
        if not row:
            return {"error": "user not found"}

        user, profile = row
        jobs_result = await db.execute(select(Job).where(Job.is_active == True))
        all_jobs = jobs_result.scalars().all()
        job_map = {str(j.id): j for j in all_jobs}

        user_embedding = await embed_profile(profile)
        top_job_ids = await get_job_ids_by_vector(user_embedding, limit=200)

        for job_id, cosine_sim in top_job_ids:
            job = job_map.get(job_id)
            if not job:
                continue
            details = compute_match_score(profile, job, cosine_sim)
            await db.execute(
                text("""
                    INSERT INTO job_match_scores (user_id, job_id, score, score_details, computed_at)
                    VALUES (:user_id, :job_id, :score, :details::jsonb, NOW())
                    ON CONFLICT (user_id, job_id) DO UPDATE
                    SET score = EXCLUDED.score, score_details = EXCLUDED.score_details, computed_at = NOW()
                """),
                {"user_id": user_id, "job_id": job_id, "score": details.total,
                 "details": str(details.to_dict()).replace("'", '"')},
            )
            scored += 1

        await db.commit()

    await engine.dispose()
    return {"user_id": user_id, "scores_computed": scored}
