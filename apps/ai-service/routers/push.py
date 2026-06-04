"""
Push notification token management.
POST /push/register   → register or update Expo push token
DELETE /push/token    → remove push token (on logout)
POST /push/test       → send test notification (dev only)
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import User
from routers.deps import get_current_user
from services.push_notifications import send_push_to_user, is_valid_expo_token

router = APIRouter(prefix="/push", tags=["push"])


class RegisterTokenRequest(BaseModel):
    token: str   # ExponentPushToken[...]
    platform: str = "unknown"  # "ios" | "android" | "unknown"


@router.post("/register", status_code=200)
async def register_push_token(
    body: RegisterTokenRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not is_valid_expo_token(body.token):
        raise HTTPException(status_code=400, detail="Invalid Expo push token format")

    # Upsert push token for user
    await db.execute(text("""
        INSERT INTO push_tokens (user_id, token, platform, updated_at)
        VALUES (:user_id, :token, :platform, NOW())
        ON CONFLICT (user_id)
        DO UPDATE SET token = EXCLUDED.token,
                      platform = EXCLUDED.platform,
                      updated_at = NOW()
    """), {
        "user_id":  str(current_user.id),
        "token":    body.token,
        "platform": body.platform,
    })
    await db.commit()
    return {"message": "Push token registered"}


@router.delete("/token", status_code=200)
async def remove_push_token(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    await db.execute(
        text("DELETE FROM push_tokens WHERE user_id = :uid"),
        {"uid": str(current_user.id)},
    )
    await db.commit()
    return {"message": "Push token removed"}


@router.post("/test")
async def test_push(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not settings.debug:
        raise HTTPException(status_code=403, detail="Test push only available in debug mode")

    result = await db.execute(
        text("SELECT token FROM push_tokens WHERE user_id = :uid"),
        {"uid": str(current_user.id)},
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="No push token registered for this user")

    success = await send_push_to_user(
        row.token,
        title="✅ SwipeHire Test",
        body="Push notifications are working!",
        data={"type": "test"},
    )
    return {"sent": success, "token": row.token[:30] + "..."}
