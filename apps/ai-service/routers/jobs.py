"""
Jobs routes.
GET  /jobs/feed         → ML-ranked job feed (excludes already swiped)
GET  /jobs/:id          → single job detail
GET  /jobs/search       → full-text search via Meilisearch
POST /jobs              → create job (recruiter only)
"""
from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, text, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from ml.recommender import rank_jobs_for_user, filter_by_preferences
from models.job import Job
from models.swipe import Swipe
from models.user import User, UserProfile
from routers.deps import get_current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class JobOut(BaseModel):
    id: str
    title: str
    company: str
    company_logo: str | None
    location: str | None
    is_remote: bool
    salary_min_lpa: float | None
    salary_max_lpa: float | None
    experience_min: float
    experience_max: float
    skills_required: list[str]
    description: str | None
    apply_url: str | None
    job_type: str | None
    industry: str | None
    source: str
    posted_at: str
    match_score: int = 0
    score_details: dict = {}
    highlights: list[str] = []

    class Config:
        from_attributes = True


class CreateJobRequest(BaseModel):
    title: str
    company: str
    location: str | None = None
    is_remote: bool = False
    salary_min_lpa: float | None = None
    salary_max_lpa: float | None = None
    experience_min: float = 0
    experience_max: float = 10
    skills_required: list[str] = []
    description: str | None = None
    apply_url: str | None = None
    job_type: str = "full-time"
    industry: str | None = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _job_to_out(job: Job, score: int = 0, score_details: dict | None = None) -> JobOut:
    return JobOut(
        id=str(job.id),
        title=job.title,
        company=job.company,
        company_logo=job.company_logo,
        location=job.location,
        is_remote=job.is_remote,
        salary_min_lpa=float(job.salary_min_lpa) if job.salary_min_lpa else None,
        salary_max_lpa=float(job.salary_max_lpa) if job.salary_max_lpa else None,
        experience_min=float(job.experience_min or 0),
        experience_max=float(job.experience_max or 50),
        skills_required=job.skills_required or [],
        description=job.description,
        apply_url=job.apply_url,
        job_type=job.job_type,
        industry=job.industry,
        source=job.source,
        posted_at=job.posted_at.isoformat(),
        match_score=score,
        score_details=score_details or {},
        highlights=_generate_highlights(job),
    )


def _generate_highlights(job: Job) -> list[str]:
    """Generate 3 quick highlights shown on the card without LLM."""
    highlights = []
    if job.is_remote:
        highlights.append("🌍 Fully Remote")
    elif job.location:
        highlights.append(f"📍 {job.location}")

    if job.salary_min_lpa and job.salary_max_lpa:
        highlights.append(f"💰 ₹{job.salary_min_lpa:.0f}–{job.salary_max_lpa:.0f} LPA")
    elif job.salary_max_lpa:
        highlights.append(f"💰 Up to ₹{job.salary_max_lpa:.0f} LPA")

    if job.experience_min == 0 and job.experience_max <= 1:
        highlights.append("🎓 Fresher friendly")
    elif job.experience_min is not None:
        highlights.append(f"🏢 {job.experience_min:.0f}–{job.experience_max:.0f} years exp")

    return highlights[:3]


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/feed", response_model=list[JobOut])
async def get_job_feed(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> list[JobOut]:
    # Get user profile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    if not profile or not profile.is_onboarded:
        # Return generic feed for new users
        jobs_result = await db.execute(
            select(Job).where(Job.is_active == True).order_by(Job.posted_at.desc()).limit(limit).offset(offset)
        )
        jobs = jobs_result.scalars().all()
        return [_job_to_out(j) for j in jobs]

    # Get swiped job IDs to exclude
    swiped_result = await db.execute(
        select(Swipe.job_id).where(Swipe.user_id == current_user.id)
    )
    swiped_ids = {str(row[0]) for row in swiped_result.all()}

    # Fetch candidate jobs (larger pool for ML to rank)
    candidate_limit = min(limit * 10, 300)
    jobs_result = await db.execute(
        select(Job)
        .where(Job.is_active == True)
        .order_by(Job.posted_at.desc())
        .limit(candidate_limit)
    )
    candidate_jobs = list(jobs_result.scalars().all())

    # Hard filter
    filtered = filter_by_preferences(candidate_jobs, profile)

    # ML ranking
    ranked = await rank_jobs_for_user(profile, filtered, swiped_ids)

    # Paginate
    page_slice = ranked[offset: offset + limit]

    return [_job_to_out(job, details.total, details.to_dict()) for job, details in page_slice]


@router.get("/search", response_model=list[JobOut])
async def search_jobs_endpoint(
    q: str = Query(..., min_length=1, description="Search query"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    is_remote: bool | None = Query(None),
    job_type: str | None = Query(None),
    location: str | None = Query(None),
    industry: str | None = Query(None),
    sort_by: str | None = Query(None, description="e.g. 'salary_max_lpa:desc'"),
) -> list[JobOut]:
    try:
        from services.search import search_jobs as meili_search

        filters: dict = {}
        if is_remote is not None:
            filters["is_remote"] = is_remote
        if job_type:
            filters["job_type"] = job_type
        if location:
            filters["location"] = location
        if industry:
            filters["industry"] = industry

        sort = [sort_by] if sort_by else ["posted_at:desc"]
        result = await meili_search(q, limit=limit, offset=offset, filters=filters, sort=sort)
        hits = result.get("hits", [])

        return [
            JobOut(
                id=h["id"],
                title=h["title"],
                company=h["company"],
                company_logo=h.get("company_logo"),
                location=h.get("location"),
                is_remote=h.get("is_remote", False),
                salary_min_lpa=h.get("salary_min_lpa"),
                salary_max_lpa=h.get("salary_max_lpa"),
                experience_min=h.get("experience_min", 0),
                experience_max=h.get("experience_max", 50),
                skills_required=h.get("skills_required", []),
                description=h.get("description"),
                apply_url=h.get("apply_url"),
                job_type=h.get("job_type"),
                industry=h.get("industry"),
                source=h.get("source", ""),
                posted_at=h.get("posted_at", ""),
            )
            for h in hits
        ]
    except Exception as e:
        # Fallback to DB search if Meilisearch unavailable
        from sqlalchemy import or_
        results = await db.execute(
            select(Job)
            .where(Job.is_active == True, Job.title.ilike(f"%{q}%") | Job.company.ilike(f"%{q}%"))
            .order_by(Job.posted_at.desc())
            .limit(limit)
            .offset(offset)
        )
        jobs = results.scalars().all()
        return [_job_to_out(j) for j in jobs]


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_out(job)


@router.post("", response_model=JobOut, status_code=201)
async def create_job(
    body: CreateJobRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> JobOut:
    job = Job(
        source="recruiter",
        title=body.title,
        company=body.company,
        location=body.location,
        is_remote=body.is_remote,
        salary_min_lpa=body.salary_min_lpa,
        salary_max_lpa=body.salary_max_lpa,
        experience_min=body.experience_min,
        experience_max=body.experience_max,
        skills_required=body.skills_required,
        description=body.description,
        apply_url=body.apply_url,
        job_type=body.job_type,
        industry=body.industry,
    )
    db.add(job)
    await db.flush()
    return _job_to_out(job)
