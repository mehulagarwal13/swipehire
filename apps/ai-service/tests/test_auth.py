"""Tests for auth endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_send_otp_success(client: AsyncClient) -> None:
    with patch("services.otp.otp_exists", return_value=False), \
         patch("services.otp.create_and_send_otp", return_value="123456") as mock_send:
        resp = await client.post("/api/v1/auth/send-otp", json={"phone": "9876543210"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "OTP sent"
    mock_send.assert_called_once_with("9876543210", debug=False)


@pytest.mark.asyncio
async def test_send_otp_spam_blocked(client: AsyncClient) -> None:
    with patch("services.otp.otp_exists", return_value=True):
        resp = await client.post("/api/v1/auth/send-otp", json={"phone": "9876543210"})

    assert resp.status_code == 429
    assert "already sent" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_verify_otp_success(client: AsyncClient) -> None:
    with patch("services.otp.verify_otp", return_value=True):
        resp = await client.post(
            "/api/v1/auth/verify-otp",
            json={"phone": "9123456789", "otp": "654321"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "user_id" in data


@pytest.mark.asyncio
async def test_verify_otp_invalid(client: AsyncClient) -> None:
    with patch("services.otp.verify_otp", return_value=False):
        resp = await client.post(
            "/api/v1/auth/verify-otp",
            json={"phone": "9876543210", "otp": "000000"},
        )

    assert resp.status_code == 400
    assert "Invalid" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user) -> None:
    from routers.auth import _create_refresh_token
    refresh = _create_refresh_token(str(test_user.id))

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not.a.token"})
    assert resp.status_code == 401
