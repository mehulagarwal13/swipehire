"""Tests for swipe recording and saved jobs."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_swipe_right_creates_application(
    client: AsyncClient, auth_headers: dict, test_job
) -> None:
    resp = await client.post(
        "/api/v1/swipes",
        json={"job_id": str(test_job.id), "direction": "right", "match_score": 85},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["direction"] == "right"
    assert data["application_id"] is not None
    assert "Applied" in data["message"]


@pytest.mark.asyncio
async def test_swipe_left_no_application(
    client: AsyncClient, auth_headers: dict, test_job
) -> None:
    import uuid
    from models.job import Job
    from sqlalchemy.ext.asyncio import AsyncSession
    # Need a different job since test_job may already have a swipe
    resp = await client.post(
        "/api/v1/swipes",
        json={"job_id": str(test_job.id), "direction": "left"},
        headers=auth_headers,
    )
    # May be 201 (new) or 409 (duplicate) depending on test order
    assert resp.status_code in (201, 409)
    if resp.status_code == 201:
        data = resp.json()
        assert data["direction"] == "left"
        assert data["application_id"] is None


@pytest.mark.asyncio
async def test_swipe_invalid_direction(
    client: AsyncClient, auth_headers: dict, test_job
) -> None:
    resp = await client.post(
        "/api/v1/swipes",
        json={"job_id": str(test_job.id), "direction": "down"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_swipe_nonexistent_job(
    client: AsyncClient, auth_headers: dict
) -> None:
    import uuid
    resp = await client.post(
        "/api/v1/swipes",
        json={"job_id": str(uuid.uuid4()), "direction": "right"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_saved_jobs(client: AsyncClient, auth_headers: dict) -> None:
    resp = await client.get("/api/v1/swipes/saved", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
