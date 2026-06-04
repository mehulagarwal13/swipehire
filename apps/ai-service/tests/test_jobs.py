"""Tests for job feed and search endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_get_job_feed_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/jobs/feed")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_job_feed_authenticated(client: AsyncClient, auth_headers: dict, test_job) -> None:
    resp = await client.get("/api/v1/jobs/feed", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_job_by_id(client: AsyncClient, auth_headers: dict, test_job) -> None:
    resp = await client.get(f"/api/v1/jobs/{test_job.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(test_job.id)
    assert data["title"] == test_job.title
    assert data["company"] == test_job.company


@pytest.mark.asyncio
async def test_get_nonexistent_job(client: AsyncClient, auth_headers: dict) -> None:
    import uuid
    resp = await client.get(f"/api/v1/jobs/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_job(client: AsyncClient, auth_headers: dict) -> None:
    payload = {
        "title": "React Developer",
        "company": "StartupXYZ",
        "location": "Hyderabad",
        "is_remote": False,
        "salary_min_lpa": 8.0,
        "salary_max_lpa": 14.0,
        "experience_min": 1.0,
        "experience_max": 3.0,
        "skills_required": ["React", "TypeScript"],
        "description": "Build our frontend.",
        "job_type": "full-time",
        "industry": "Engineering",
    }
    resp = await client.post("/api/v1/jobs", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == payload["title"]
    assert data["source"] == "recruiter"


@pytest.mark.asyncio
async def test_search_jobs_meilisearch(client: AsyncClient, auth_headers: dict) -> None:
    mock_result = {
        "hits": [
            {
                "id": "abc123",
                "title": "Python Developer",
                "company": "Infosys",
                "location": "Bangalore",
                "is_remote": False,
                "salary_min_lpa": 8.0,
                "salary_max_lpa": 15.0,
                "experience_min": 2.0,
                "experience_max": 4.0,
                "skills_required": ["Python", "Django"],
                "description": "Great role",
                "apply_url": "https://infosys.com/careers",
                "job_type": "full-time",
                "industry": "Engineering",
                "source": "naukri",
                "posted_at": "2026-01-01T00:00:00",
            }
        ],
        "estimatedTotalHits": 1,
    }
    with patch("services.search.search_jobs", return_value=mock_result):
        resp = await client.get("/api/v1/jobs/search?q=python", headers=auth_headers)

    assert resp.status_code == 200
    hits = resp.json()
    assert len(hits) == 1
    assert hits[0]["title"] == "Python Developer"
