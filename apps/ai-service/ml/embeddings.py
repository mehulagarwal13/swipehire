"""
Embedding service — converts user profiles and job descriptions into dense vectors
for cosine-similarity matching. Uses sentence-transformers locally (no API cost).
Swap _MODEL_NAME to "text-embedding-3-small" + OpenAI client for higher accuracy.
"""
from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np
from sentence_transformers import SentenceTransformer

from config import settings

if TYPE_CHECKING:
    from models.user import UserProfile
    from models.job import Job


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Load model once and cache it — ~80 MB in memory."""
    return SentenceTransformer(settings.embedding_model)


def _encode(text: str) -> list[float]:
    model = _get_model()
    vec: np.ndarray = model.encode(text, normalize_embeddings=True)
    return vec.tolist()


async def embed_text(text: str) -> list[float]:
    """Non-blocking wrapper — runs CPU-bound encode in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _encode, text)


def build_profile_text(profile: "UserProfile") -> str:
    skills_str = " ".join(profile.skills or [])
    locations = " ".join(profile.preferred_locations or [])
    job_types = " ".join(profile.job_types or [])

    edu_parts = []
    for edu in (profile.education or []):
        if isinstance(edu, dict):
            edu_parts.append(f"{edu.get('degree','')} {edu.get('college','')}")

    exp_parts = []
    for exp in (profile.experience or []):
        if isinstance(exp, dict):
            exp_parts.append(f"{exp.get('role','')} at {exp.get('company','')}: {exp.get('description','')}")

    proj_parts = []
    for proj in (profile.projects or []):
        if isinstance(proj, dict):
            proj_parts.append(f"{proj.get('name','')} {proj.get('stack','')} {proj.get('desc','')}")

    return (
        f"Skills: {skills_str}. "
        f"Experience: {profile.experience_years} years. "
        f"Headline: {profile.headline or ''}. "
        f"Location preference: {locations}. "
        f"Job type: {job_types}. "
        f"Education: {' '.join(edu_parts)}. "
        f"Work history: {' '.join(exp_parts)}. "
        f"Projects: {' '.join(proj_parts)}."
    )


def build_job_text(job: "Job") -> str:
    skills_str = " ".join(job.skills_required or [])
    remote = "remote" if job.is_remote else ""
    return (
        f"{job.title} at {job.company}. "
        f"Location: {job.location or ''} {remote}. "
        f"Skills required: {skills_str}. "
        f"Description: {(job.description or '')[:500]}."
    )


async def embed_profile(profile: "UserProfile") -> list[float]:
    return await embed_text(build_profile_text(profile))


async def embed_job(job: "Job") -> list[float]:
    return await embed_text(build_job_text(job))
