"""
Match scoring algorithm — weighted composite of 5 signals.

Score = skill_overlap(0.35) + experience(0.20) + location(0.15)
      + salary(0.15) + semantic_similarity(0.15)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fuzzywuzzy import fuzz

if TYPE_CHECKING:
    from models.user import UserProfile
    from models.job import Job

# ─── Tier definitions for India-specific location scoring ─────────────────────
_TIER1 = {"bangalore", "bengaluru", "mumbai", "delhi", "delhi ncr", "gurgaon", "noida", "hyderabad", "pune", "chennai"}
_TIER2 = {"kolkata", "ahmedabad", "jaipur", "lucknow", "surat", "kochi", "indore", "nagpur", "bhopal"}


@dataclass
class ScoreDetails:
    skill_score: int
    experience_score: int
    location_score: int
    salary_score: int
    semantic_score: int
    total: int

    def to_dict(self) -> dict:
        return {
            "skills": self.skill_score,
            "experience": self.experience_score,
            "location": self.location_score,
            "salary": self.salary_score,
            "semantic": self.semantic_score,
        }


# ─── Individual signal scorers ────────────────────────────────────────────────

def skill_overlap_score(user_skills: list[str], job_skills: list[str]) -> int:
    """Hybrid exact + fuzzy skill matching (handles ReactJS vs React.js)."""
    if not job_skills:
        return 80  # no requirements = broadly open role

    user_set = {s.lower().strip() for s in user_skills}
    job_set = {s.lower().strip() for s in job_skills}

    # Exact matches
    exact_hits = len(user_set & job_set)
    exact_ratio = exact_hits / len(job_set)

    # Fuzzy matches for the remaining
    unmatched_job = job_set - user_set

    if not unmatched_job:
        # All job skills matched exactly — perfect match
        return min(round(exact_ratio * 100), 100)

    fuzzy_hits = sum(
        1 for js in unmatched_job
        if any(fuzz.ratio(js, us) > 82 for us in user_set)
    )
    fuzzy_ratio = fuzzy_hits / len(job_set)

    raw = exact_ratio * 0.70 + fuzzy_ratio * 0.30
    return min(round(raw * 100), 100)


def experience_score(user_years: float, job_min: float, job_max: float) -> int:
    """Penalise under-qualification; slight penalty for overqualification."""
    if user_years < job_min:
        gap = job_min - user_years
        return max(0, round(100 - gap * 22))
    if user_years > job_max + 3:
        return 72  # overqualified
    return 100


def location_score(
    user_preferred: list[str],
    job_location: str | None,
    is_remote: bool,
) -> int:
    if is_remote:
        return 100
    if not job_location:
        return 70

    job_loc = job_location.lower()
    user_locs = [l.lower() for l in (user_preferred or [])]

    # Exact / substring match
    for ul in user_locs:
        if ul in job_loc or job_loc in ul:
            return 100

    # Same tier (e.g., user wants Bangalore, job is in Pune — both Tier 1)
    job_tier = _get_tier(job_loc)
    if any(_get_tier(ul) == job_tier and job_tier != 0 for ul in user_locs):
        return 65

    return 30


def _get_tier(loc: str) -> int:
    if any(t in loc for t in _TIER1):
        return 1
    if any(t in loc for t in _TIER2):
        return 2
    return 3


def salary_score(
    user_min: float | None,
    user_max: float | None,
    job_min: float | None,
    job_max: float | None,
) -> int:
    """Score salary compatibility. Missing data = neutral 70."""
    if not job_min and not job_max:
        return 70
    if not user_min and not user_max:
        return 70

    # Use midpoints
    user_mid = ((user_min or 0) + (user_max or user_min or 0)) / 2
    job_mid = ((job_min or 0) + (job_max or job_min or 0)) / 2

    if job_mid == 0:
        return 70

    ratio = user_mid / job_mid
    if 0.85 <= ratio <= 1.20:
        return 100  # great match
    if 0.70 <= ratio <= 1.40:
        return 80
    if ratio > 1.40:
        return 50  # user expects much more than job pays
    return 65  # user expects much less — may be underpaid


def semantic_score(cosine_sim: float) -> int:
    """Convert 0–1 cosine similarity to 0–100 integer score."""
    return min(round(cosine_sim * 100), 100)


# ─── Composite scorer ─────────────────────────────────────────────────────────

def compute_match_score(
    profile: "UserProfile",
    job: "Job",
    cosine_sim: float = 0.0,
) -> ScoreDetails:
    sk = skill_overlap_score(profile.skills or [], job.skills_required or [])
    ex = experience_score(
        float(profile.experience_years or 0),
        float(job.experience_min or 0),
        float(job.experience_max or 50),
    )
    lo = location_score(
        profile.preferred_locations or [],
        job.location,
        job.is_remote,
    )
    sa = salary_score(
        float(profile.min_salary_lpa) if profile.min_salary_lpa else None,
        float(profile.max_salary_lpa) if profile.max_salary_lpa else None,
        float(job.salary_min_lpa) if job.salary_min_lpa else None,
        float(job.salary_max_lpa) if job.salary_max_lpa else None,
    )
    sem = semantic_score(cosine_sim)

    total = round(
        sk * 0.35
        + ex * 0.20
        + lo * 0.15
        + sa * 0.15
        + sem * 0.15
    )

    return ScoreDetails(
        skill_score=sk,
        experience_score=ex,
        location_score=lo,
        salary_score=sa,
        semantic_score=sem,
        total=total,
    )
