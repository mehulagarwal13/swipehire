"""
Auto-apply route.
POST /auto-apply/:job_id  → trigger auto-apply for a right-swiped job
GET  /auto-apply/:app_id/status → check apply result
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.job import Job
from models.swipe import Application
from models.user import User, UserProfile
from routers.deps import get_current_user
from services.auto_apply import AutoApplyWorker, UserApplyData

router = APIRouter(prefix="/auto-apply", tags=["auto-apply"])


async def _run_auto_apply(app_id: str, apply_url: str, user_data: UserApplyData, db_url: str) -> None:
    """Background task — runs after response is sent."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from config import settings

    worker = AutoApplyWorker()
    result = await worker.run(apply_url, user_data)

    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db:
        res = await db.execute(select(Application).where(Application.id == app_id))
        app = res.scalar_one_or_none()
        if app:
            app.auto_applied = result.success
            app.notes = (
                f"Auto-applied via {result.portal} — {result.confirmation_url}"
                if result.success
                else f"Auto-apply failed: {result.error}"
            )
            await db.commit()

    await engine.dispose()


@router.post("/{job_id}")
async def trigger_auto_apply(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Check plan
    if current_user.plan == "free":
        raise HTTPException(status_code=403, detail="Auto-apply requires Pro or Premium plan")

    # Get job
    job_res = await db.execute(select(Job).where(Job.id == job_id))
    job = job_res.scalar_one_or_none()
    if not job or not job.apply_url:
        raise HTTPException(status_code=404, detail="Job or apply URL not found")

    # Get profile
    profile_res = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = profile_res.scalar_one_or_none()
    if not profile or not profile.resume_url:
        raise HTTPException(status_code=400, detail="Upload a resume before auto-applying")

    # Get or create application record
    app_res = await db.execute(
        select(Application).where(
            Application.user_id == current_user.id,
            Application.job_id == job_id,
        )
    )
    app = app_res.scalar_one_or_none()
    if not app:
        app = Application(
            user_id=current_user.id,
            job_id=job_id,
            status="applied",
            auto_applied=False,
        )
        db.add(app)
        await db.flush()

    user_data = UserApplyData(
        full_name=current_user.full_name or "",
        email=current_user.email or "",
        phone=current_user.phone or "",
        resume_url=profile.resume_url,
        headline=profile.headline or "",
        current_location=profile.current_location or "",
        experience_years=float(profile.experience_years or 0),
        notice_period_days=profile.notice_period_days or 30,
        expected_salary_lpa=float(profile.max_salary_lpa or 0),
    )

    from config import settings
    background_tasks.add_task(
        _run_auto_apply,
        str(app.id),
        job.apply_url,
        user_data,
        settings.database_url,
    )

    return {
        "message": "Auto-apply queued",
        "application_id": str(app.id),
        "job": {"title": job.title, "company": job.company},
    }
