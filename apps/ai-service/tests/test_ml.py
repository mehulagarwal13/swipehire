"""Tests for ML scoring and recommendation logic."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from ml.scorer import (
    skill_overlap_score,
    experience_score,
    location_score,
    salary_score,
    semantic_score,
    compute_match_score,
)


# ─── Skill overlap ────────────────────────────────────────────────────────────

class TestSkillOverlapScore:
    def test_perfect_match(self):
        assert skill_overlap_score(["Python", "React"], ["Python", "React"]) == 100

    def test_no_match(self):
        score = skill_overlap_score(["Java", "Spring"], ["Python", "FastAPI"])
        assert score == 0

    def test_partial_match(self):
        score = skill_overlap_score(["Python", "React", "SQL"], ["Python", "FastAPI", "PostgreSQL"])
        # Python matches, FastAPI/PostgreSQL don't exactly — but fuzzy may catch PostgreSQL≈SQL
        assert 0 < score <= 100

    def test_fuzzy_match(self):
        # "ReactJS" vs "React.js" should fuzzy-match
        score = skill_overlap_score(["ReactJS"], ["React.js"])
        assert score > 0

    def test_no_job_skills_returns_80(self):
        assert skill_overlap_score(["Python"], []) == 80

    def test_case_insensitive(self):
        score = skill_overlap_score(["python", "REACT"], ["Python", "React"])
        assert score == 100


# ─── Experience score ─────────────────────────────────────────────────────────

class TestExperienceScore:
    def test_within_range(self):
        assert experience_score(3.0, 2.0, 5.0) == 100

    def test_underqualified_slightly(self):
        score = experience_score(1.0, 2.0, 4.0)
        assert 0 < score < 100

    def test_severely_underqualified(self):
        score = experience_score(0.0, 5.0, 8.0)
        assert score == 0

    def test_overqualified(self):
        score = experience_score(15.0, 1.0, 3.0)
        assert score == 72

    def test_fresher_for_fresher_role(self):
        assert experience_score(0.0, 0.0, 1.0) == 100


# ─── Location score ───────────────────────────────────────────────────────────

class TestLocationScore:
    def test_remote_always_100(self):
        assert location_score(["Bangalore"], None, True) == 100

    def test_exact_location_match(self):
        assert location_score(["Bangalore"], "Bangalore, KA", False) == 100

    def test_no_location(self):
        assert location_score(["Bangalore"], None, False) == 70

    def test_different_tier1_cities(self):
        score = location_score(["Bangalore"], "Mumbai, MH", False)
        assert score == 65  # same tier

    def test_no_match_different_tiers(self):
        score = location_score(["Bangalore"], "Jaipur", False)
        assert score < 70


# ─── Salary score ─────────────────────────────────────────────────────────────

class TestSalaryScore:
    def test_perfect_salary_match(self):
        assert salary_score(8.0, 15.0, 8.0, 15.0) == 100

    def test_missing_data_neutral(self):
        assert salary_score(None, None, None, None) == 70

    def test_user_expects_too_much(self):
        score = salary_score(30.0, 40.0, 5.0, 8.0)
        assert score == 50

    def test_underpaid(self):
        score = salary_score(3.0, 5.0, 20.0, 30.0)
        assert score == 65


# ─── Semantic score ───────────────────────────────────────────────────────────

class TestSemanticScore:
    def test_high_similarity(self):
        assert semantic_score(0.95) == 95

    def test_low_similarity(self):
        assert semantic_score(0.20) == 20

    def test_clamps_at_100(self):
        assert semantic_score(1.5) == 100


# ─── Composite scorer ─────────────────────────────────────────────────────────

class TestComputeMatchScore:
    def _make_profile(self):
        p = MagicMock()
        p.skills = ["Python", "FastAPI", "React"]
        p.experience_years = 3.0
        p.preferred_locations = ["Bangalore"]
        p.min_salary_lpa = 8.0
        p.max_salary_lpa = 15.0
        p.job_types = ["full-time"]
        return p

    def _make_job(self):
        j = MagicMock()
        j.skills_required = ["Python", "FastAPI", "PostgreSQL"]
        j.experience_min = 2.0
        j.experience_max = 5.0
        j.location = "Bangalore"
        j.is_remote = False
        j.salary_min_lpa = 10.0
        j.salary_max_lpa = 18.0
        j.job_type = "full-time"
        return j

    def test_high_match_score(self):
        profile = self._make_profile()
        job     = self._make_job()
        details = compute_match_score(profile, job, cosine_sim=0.88)
        assert details.total >= 75
        assert 0 <= details.skill_score <= 100
        assert 0 <= details.experience_score <= 100

    def test_low_match_score(self):
        profile = self._make_profile()
        job = self._make_job()
        job.skills_required = ["COBOL", "Mainframe", "AS400"]
        job.experience_min = 10.0
        job.salary_max_lpa = 3.0
        details = compute_match_score(profile, job, cosine_sim=0.10)
        assert details.total < 60

    def test_score_details_dict(self):
        profile = self._make_profile()
        job = self._make_job()
        details = compute_match_score(profile, job)
        d = details.to_dict()
        assert set(d.keys()) == {"skills", "experience", "location", "salary", "semantic"}
        assert all(0 <= v <= 100 for v in d.values())
