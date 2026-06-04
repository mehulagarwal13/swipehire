"""
Profile routes.
GET  /profile          → get current user's profile
PUT  /profile          → update profile preferences
POST /profile/resume   → upload + parse resume
GET  /profile/score    → get profile completeness score
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from ml.embeddings import embed_profile
try:
    from ml.resume_parser import parse_resume as _parse_resume_fn
except ImportError:
    _parse_resume_fn = None  # type: ignore[assignment]

async def parse_resume(file_bytes: bytes, content_type: str):  # type: ignore[misc]
    if _parse_resume_fn is None:
        raise RuntimeError("Resume parser is not available: install pdfplumber and pytesseract.")
    return await _parse_resume_fn(file_bytes, content_type)
from models.user import User, UserProfile
from routers.deps import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])

MAX_RESUME_SIZE = 5 * 1024 * 1024  # 5 MB


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    headline: str | None = None
    skills: list[str] | None = None
    experience_years: float | None = None
    current_location: str | None = None
    preferred_locations: list[str] | None = None
    min_salary_lpa: float | None = None
    max_salary_lpa: float | None = None
    job_types: list[str] | None = None
    notice_period_days: int | None = None
    education: list[dict] | None = None
    experience: list[dict] | None = None
    projects: list[dict] | None = None


class ProfileOut(BaseModel):
    user_id: str
    full_name: str | None
    email: str | None
    phone: str | None
    headline: str | None
    skills: list[str]
    experience_years: float
    current_location: str | None
    preferred_locations: list[str]
    min_salary_lpa: float | None
    max_salary_lpa: float | None
    job_types: list[str]
    notice_period_days: int
    education: list
    experience: list
    projects: list
    profile_score: int
    is_onboarded: bool
    resume_url: str | None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _compute_profile_score(profile: UserProfile) -> int:
    """Returns 0–100 completeness score."""
    score = 0
    if profile.headline:            score += 10
    if profile.skills:              score += 20
    if profile.experience_years:    score += 10
    if profile.current_location:    score += 5
    if profile.preferred_locations: score += 5
    if profile.min_salary_lpa:      score += 5
    if profile.job_types:           score += 5
    if profile.education:           score += 15
    if profile.experience:          score += 15
    if profile.resume_url:          score += 10
    return min(score, 100)


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("", response_model=ProfileOut)
async def get_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return ProfileOut(
        user_id=str(current_user.id),
        full_name=current_user.full_name,
        email=current_user.email,
        phone=current_user.phone,
        headline=profile.headline,
        skills=profile.skills or [],
        experience_years=float(profile.experience_years or 0),
        current_location=profile.current_location,
        preferred_locations=profile.preferred_locations or [],
        min_salary_lpa=float(profile.min_salary_lpa) if profile.min_salary_lpa else None,
        max_salary_lpa=float(profile.max_salary_lpa) if profile.max_salary_lpa else None,
        job_types=profile.job_types or [],
        notice_period_days=profile.notice_period_days or 30,
        education=profile.education or [],
        experience=profile.experience or [],
        projects=profile.projects or [],
        profile_score=profile.profile_score,
        is_onboarded=profile.is_onboarded,
        resume_url=profile.resume_url,
    )


@router.put("", response_model=ProfileOut)
async def update_profile(
    body: ProfileUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Apply updates (only set fields)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(profile, field, value)

    profile.profile_score = _compute_profile_score(profile)

    # Mark onboarded if key fields are filled
    if profile.skills and profile.preferred_locations and profile.job_types:
        profile.is_onboarded = True

    # Regenerate embedding asynchronously
    if body.skills or body.experience or body.headline:
        try:
            embedding = await embed_profile(profile)
            await db.execute(
                text("UPDATE user_profiles SET embedding_vector = :vec WHERE id = :id"),
                {"vec": str(embedding), "id": profile.id},
            )
        except Exception:
            pass  # embedding failure shouldn't block profile save

    await db.flush()
    return await get_profile(current_user, db)


@router.post("/resume")
async def upload_resume(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
) -> dict:
    if file.size and file.size > MAX_RESUME_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 5 MB.")

    allowed_types = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Only PDF and DOCX supported")

    file_bytes = await file.read()

    # Parse resume
    parsed = await parse_resume(file_bytes, file.content_type or "application/pdf")

    # Update profile with parsed data
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    if parsed.skills:
        profile.skills = parsed.skills
    if parsed.experience_years:
        profile.experience_years = parsed.experience_years
    if parsed.education:
        profile.education = [e.model_dump() for e in parsed.education]
    if parsed.experience:
        profile.experience = [e.model_dump() for e in parsed.experience]
    if parsed.projects:
        profile.projects = [p.model_dump() for p in parsed.projects]
    if parsed.headline:
        profile.headline = parsed.headline
    if parsed.current_location:
        profile.current_location = parsed.current_location

    # Update user name if parsed
    if parsed.full_name and not current_user.full_name:
        current_user.full_name = parsed.full_name

    profile.profile_score = _compute_profile_score(profile)
    await db.flush()

    return {
        "message": "Resume parsed successfully",
        "parsed": parsed.model_dump(),
        "profile_score": profile.profile_score,
    }


@router.get("/score")
async def get_profile_score(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    if not profile:
        return {"score": 0, "missing": ["Complete your profile to get started"]}

    score = _compute_profile_score(profile)
    missing = []
    if not profile.headline:            missing.append("Add a headline")
    if not profile.skills:              missing.append("Add your skills")
    if not profile.preferred_locations: missing.append("Set location preferences")
    if not profile.job_types:           missing.append("Choose job type (full-time, internship...)")
    if not profile.education:           missing.append("Add education details")
    if not profile.resume_url:          missing.append("Upload your resume")

    return {"score": score, "missing": missing}
