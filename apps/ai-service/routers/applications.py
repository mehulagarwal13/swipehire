"""
Application tracker routes.
GET   /applications         → list all applications (kanban data)
GET   /applications/:id     → get one application
PATCH /applications/:id/status → update status
DELETE /applications/:id    → withdraw application
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.job import Job
from models.swipe import Application
from models.user import User
from routers.deps import get_current_user

router = APIRouter(prefix="/applications", tags=["applications"])

# Valid state machine transitions
_VALID_TRANSITIONS: dict[str, list[str]] = {
    "applied":              ["screening", "rejected", "withdrawn"],
    "screening":            ["interview_scheduled", "rejected", "withdrawn"],
    "interview_scheduled":  ["interview_completed", "rejected", "withdrawn"],
    "interview_completed":  ["offer_extended", "rejected", "withdrawn"],
    "offer_extended":       ["offer_accepted", "offer_rejected", "withdrawn"],
    "offer_accepted":       [],
    "offer_rejected":       [],
    "rejected":             [],
    "withdrawn":            [],
}


class StatusUpdate(BaseModel):
    status: str
    notes: str | None = None
    interview_date: str | None = None  # ISO string
    offer_amount: float | None = None


class ApplicationOut(BaseModel):
    id: str
    job_id: str
    title: str
    company: str
    company_logo: str | None
    location: str | None
    status: str
    applied_at: str
    updated_at: str
    auto_applied: bool
    notes: str | None
    interview_date: str | None
    offer_amount: float | None
    match_score: int | None


@router.get("", response_model=list[ApplicationOut])
async def list_applications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> list[ApplicationOut]:
    result = await db.execute(
        select(Application, Job)
        .join(Job, Job.id == Application.job_id)
        .where(Application.user_id == current_user.id)
        .order_by(Application.applied_at.desc())
    )
    rows = result.all()

    return [
        ApplicationOut(
            id=str(app.id),
            job_id=str(job.id),
            title=job.title,
            company=job.company,
            company_logo=job.company_logo,
            location=job.location,
            status=app.status,
            applied_at=app.applied_at.isoformat(),
            updated_at=app.updated_at.isoformat(),
            auto_applied=app.auto_applied,
            notes=app.notes,
            interview_date=app.interview_date.isoformat() if app.interview_date else None,
            offer_amount=float(app.offer_amount) if app.offer_amount else None,
            match_score=None,
        )
        for app, job in rows
    ]


@router.patch("/{app_id}/status", response_model=ApplicationOut)
async def update_status(
    app_id: str,
    body: StatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ApplicationOut:
    result = await db.execute(
        select(Application, Job)
        .join(Job, Job.id == Application.job_id)
        .where(Application.id == app_id, Application.user_id == current_user.id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")

    app, job = row

    # Validate state machine
    allowed = _VALID_TRANSITIONS.get(app.status, [])
    if body.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{app.status}' to '{body.status}'. Allowed: {allowed}",
        )

    app.status = body.status
    if body.notes:
        app.notes = body.notes
    if body.offer_amount:
        app.offer_amount = body.offer_amount
    if body.interview_date:
        from datetime import datetime
        app.interview_date = datetime.fromisoformat(body.interview_date)

    await db.flush()

    return ApplicationOut(
        id=str(app.id),
        job_id=str(job.id),
        title=job.title,
        company=job.company,
        company_logo=job.company_logo,
        location=job.location,
        status=app.status,
        applied_at=app.applied_at.isoformat(),
        updated_at=app.updated_at.isoformat(),
        auto_applied=app.auto_applied,
        notes=app.notes,
        interview_date=app.interview_date.isoformat() if app.interview_date else None,
        offer_amount=float(app.offer_amount) if app.offer_amount else None,
        match_score=None,
    )


@router.delete("/{app_id}", status_code=200)
async def withdraw_application(
    app_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Application).where(Application.id == app_id, Application.user_id == current_user.id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    app.status = "withdrawn"
    await db.flush()
    return {"message": "Application withdrawn"}
