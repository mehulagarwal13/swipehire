"""
Gmail OAuth routes.
GET  /gmail/connect          → redirect to Google OAuth consent screen
GET  /gmail/callback         → handle OAuth callback, store tokens
DELETE /gmail/disconnect     → revoke and delete tokens
GET  /gmail/sync             → manually trigger email sync for current user
"""
from __future__ import annotations

import urllib.parse
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from config import settings
from database import get_db
from models.user import User
from routers.deps import get_current_user

router = APIRouter(prefix="/gmail", tags=["gmail"])

SCOPES = "https://www.googleapis.com/auth/gmail.readonly"
REDIRECT_URI = f"{settings.app_url}/api/v1/gmail/callback"


@router.get("/connect")
async def gmail_connect(
    current_user: Annotated[User, Depends(get_current_user)],
) -> RedirectResponse:
    """Redirect user to Google OAuth consent screen."""
    params = {
        "client_id":     settings.google_client_id,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "scope":         SCOPES,
        "access_type":   "offline",
        "prompt":        "consent",
        "state":         str(current_user.id),
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
    return RedirectResponse(auth_url)


@router.get("/callback")
async def gmail_callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle OAuth callback, exchange code for tokens, store in DB."""
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://oauth2.googleapis.com/token", data={
            "code":          code,
            "client_id":     settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri":  REDIRECT_URI,
            "grant_type":    "authorization_code",
        })
        resp.raise_for_status()
        tokens = resp.json()

    # Upsert tokens for user
    await db.execute(text("""
        INSERT INTO gmail_tokens (user_id, access_token, refresh_token, updated_at)
        VALUES (:user_id, :access, :refresh, NOW())
        ON CONFLICT (user_id) DO UPDATE
        SET access_token = EXCLUDED.access_token,
            refresh_token = EXCLUDED.refresh_token,
            updated_at = NOW()
    """), {
        "user_id": state,
        "access":  tokens["access_token"],
        "refresh": tokens.get("refresh_token", ""),
    })
    await db.commit()

    return {"message": "Gmail connected. Application status sync is now active."}


@router.delete("/disconnect", status_code=200)
async def gmail_disconnect(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    await db.execute(
        text("DELETE FROM gmail_tokens WHERE user_id = :uid"),
        {"uid": str(current_user.id)},
    )
    await db.commit()
    return {"message": "Gmail disconnected"}


@router.post("/sync")
async def gmail_sync_now(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Manually trigger email sync for current user."""
    from services.email_sync import sync_applications_from_gmail
    summary = await sync_applications_from_gmail(str(current_user.id), db)
    return summary
