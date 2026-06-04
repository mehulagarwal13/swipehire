"""
Swipe routes.
POST /swipes          → record a swipe (right=apply, left=skip, up=save)
GET  /swipes/saved    → list saved (up-swiped) jobs
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.job import Job
from models.swipe import Application, Swipe
from models.user import User
from routers.deps import get_current_user

router = APIRouter(prefix="/swipes", tags=["swipes"])


class SwipeRequest(BaseModel):
    job_id: str
    direction: str  # "right" | "left" | "up"
    match_score: int | None = None


class SwipeResponse(BaseModel):
    id: str
    direction: str
    application_id: str | None = None
    message: str


@router.post("", response_model=SwipeResponse, status_code=201)
async def record_swipe(
    body: SwipeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> SwipeResponse:
    if body.direction not in ("right", "left", "up"):
        raise HTTPException(status_code=400, detail="direction must be right, left, or up")

    # Verify job exists
    job_result = await db.execute(select(Job).where(Job.id == body.job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check for duplicate swipe
    existing = await db.execute(
        select(Swipe).where(Swipe.user_id == current_user.id, Swipe.job_id == body.job_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already swiped on this job")

    # Record swipe
    swipe = Swipe(
        user_id=current_user.id,
        job_id=body.job_id,
        direction=body.direction,
        match_score=body.match_score,
    )
    db.add(swipe)
    await db.flush()

    # If right-swipe → create application record
    application_id = None
    if body.direction == "right":
        app = Application(
            user_id=current_user.id,
            job_id=body.job_id,
            swipe_id=swipe.id,
            status="applied",
            auto_applied=False,
        )
        db.add(app)
        await db.flush()
        application_id = str(app.id)

    messages = {
        "right": f"Applied to {job.title} at {job.company}!",
        "left": "Job skipped.",
        "up": f"{job.title} saved to your list.",
    }

    return SwipeResponse(
        id=str(swipe.id),
        direction=body.direction,
        application_id=application_id,
        message=messages[body.direction],
    )


@router.get("/saved")
async def get_saved_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        select(Swipe, Job)
        .join(Job, Job.id == Swipe.job_id)
        .where(Swipe.user_id == current_user.id, Swipe.direction == "up")
        .order_by(Swipe.swiped_at.desc())
    )
    rows = result.all()
    return [
        {
            "swipe_id": str(swipe.id),
            "job_id": str(job.id),
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "saved_at": swipe.swiped_at.isoformat(),
        }
        for swipe, job in rows
    ]
