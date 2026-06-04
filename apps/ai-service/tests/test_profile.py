"""Tests for profile endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_profile_authenticated(
    client: AsyncClient, auth_headers: dict, test_user
) -> None:
    resp = await client.get("/api/v1/profile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == str(test_user.id)
    assert isinstance(data["skills"], list)


@pytest.mark.asyncio
async def test_get_profile_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/profile")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient, auth_headers: dict) -> None:
    payload = {
        "headline": "Senior Python Developer",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Redis"],
        "experience_years": 4.0,
        "preferred_locations": ["Bangalore", "Remote"],
        "min_salary_lpa": 12.0,
        "max_salary_lpa": 20.0,
        "job_types": ["full-time"],
        "notice_period_days": 30,
    }
    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "ml.embeddings.embed_profile", return_value=[0.1] * 384
    ):
        resp = await client.put("/api/v1/profile", json=payload, headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["headline"] == payload["headline"]
    assert "Python" in data["skills"]
    assert data["is_onboarded"] is True


@pytest.mark.asyncio
async def test_get_profile_score(client: AsyncClient, auth_headers: dict) -> None:
    resp = await client.get("/api/v1/profile/score", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "score" in data
    assert "missing" in data
    assert isinstance(data["score"], int)
    assert 0 <= data["score"] <= 100


@pytest.mark.asyncio
async def test_upload_resume_invalid_type(client: AsyncClient, auth_headers: dict) -> None:
    import io
    fake_file = io.BytesIO(b"not a pdf")
    resp = await client.post(
        "/api/v1/profile/resume",
        files={"file": ("resume.txt", fake_file, "text/plain")},
        headers=auth_headers,
    )
    assert resp.status_code == 415
