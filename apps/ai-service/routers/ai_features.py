"""
AI Premium features router.
POST /ai/resume-rewrite/:job_id  → rewrite resume for a specific job (Premium)
POST /ai/interview-prep/:job_id  → generate interview questions + answers (Premium)
"""
from __future__ import annotations

import json
import logging
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.job import Job
from models.user import User, UserProfile
from routers.deps import get_current_user
from services.resume_rewriter import rewrite_resume_for_job

router = APIRouter(prefix="/ai", tags=["ai-features"])
log = logging.getLogger(__name__)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ResumeRewriteResponse(BaseModel):
    summary: str
    highlighted_skills: list[str]
    tailored_bullets: list[str]
    cover_letter: str
    ats_keywords: list[str]
    match_tips: list[str]


class InterviewPrepResponse(BaseModel):
    company_overview: str
    questions: list[dict]   # [{question, tip, sample_answer}]
    salary_insight: str


# ─── Resume Rewriter ──────────────────────────────────────────────────────────

@router.post("/resume-rewrite/{job_id}", response_model=ResumeRewriteResponse)
async def resume_rewrite(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> ResumeRewriteResponse:
    # Premium gate
    if current_user.plan not in ("premium",):
        raise HTTPException(
            status_code=403,
            detail="Resume AI rewrite requires Premium plan (₹699/month). Upgrade at swipehire.in/upgrade",
        )

    # Get job
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get profile
    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=400, detail="Complete your profile first")

    try:
        result = await rewrite_resume_for_job(profile, current_user, job)
        return ResumeRewriteResponse(
            summary=result.summary,
            highlighted_skills=result.highlighted_skills,
            tailored_bullets=result.tailored_bullets,
            cover_letter=result.cover_letter,
            ats_keywords=result.ats_keywords,
            match_tips=result.match_tips,
        )
    except Exception as e:
        log.error("Resume rewrite failed: %s", e)
        raise HTTPException(status_code=500, detail=f"AI rewrite failed: {str(e)}")


# ─── Interview Prep ───────────────────────────────────────────────────────────

_INTERVIEW_PROMPT = """
You are an expert interview coach for the Indian tech industry.

Generate interview preparation for this candidate and role:
Candidate: {full_name}, {exp_years} years exp, skills: {skills}
Job: {job_title} at {company}
Job Description: {job_desc}

Return ONLY valid JSON:
{{
  "company_overview": "2-3 sentences about {company} — what they do, culture, recent news",
  "questions": [
    {{
      "question": "Tell me about yourself",
      "tip": "Tailor to {company}'s tech stack and values",
      "sample_answer": "3-4 sentence answer using candidate's actual background"
    }}
  ],
  "salary_insight": "For {job_title} at {company} in India, typical range is X-Y LPA. Negotiate by..."
}}

Generate 8 questions: 2 HR, 3 technical (based on required skills), 2 behavioral, 1 company-specific.
"""


@router.post("/interview-prep/{job_id}", response_model=InterviewPrepResponse)
async def interview_prep(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> InterviewPrepResponse:
    # Premium gate
    if current_user.plan not in ("premium",):
        raise HTTPException(
            status_code=403,
            detail="Interview prep requires Premium plan (₹699/month)",
        )

    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profile_result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    prompt = _INTERVIEW_PROMPT.format(
        full_name=current_user.full_name or "Candidate",
        exp_years=profile.experience_years if profile else 0,
        skills=", ".join(profile.skills if profile else []),
        job_title=job.title,
        company=job.company,
        job_desc=(job.description or "")[:800],
    )

    try:
        from services.resume_rewriter import _call_llm
        raw = await _call_llm(prompt)

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError("Invalid LLM response")

        data = json.loads(match.group())
        return InterviewPrepResponse(
            company_overview=data.get("company_overview", ""),
            questions=data.get("questions", []),
            salary_insight=data.get("salary_insight", ""),
        )
    except Exception as e:
        log.error("Interview prep failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
