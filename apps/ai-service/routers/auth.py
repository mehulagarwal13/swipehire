"""
Auth routes — Phone OTP + Google OAuth + JWT issuance.
POST /auth/send-otp   → send OTP to phone
POST /auth/verify-otp → verify OTP, return JWT pair
POST /auth/google     → google id_token → JWT pair
POST /auth/refresh    → refresh token → new access token
POST /auth/logout     → revoke refresh token
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import User, UserProfile

router = APIRouter(prefix="/auth", tags=["auth"])

# ─── Schemas ──────────────────────────────────────────────────────────────────

class SendOtpRequest(BaseModel):
    phone: str  # e.g. "9876543210" (without +91)

class VerifyOtpRequest(BaseModel):
    phone: str
    otp: str

class GoogleAuthRequest(BaseModel):
    id_token: str
    email: EmailStr
    full_name: str | None = None

class RefreshRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    is_onboarded: bool


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "access"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def _create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=30)
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "refresh"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


async def _get_or_create_user(
    db: AsyncSession,
    *,
    phone: str | None = None,
    email: str | None = None,
    full_name: str | None = None,
) -> User:
    query = select(User)
    if phone:
        query = query.where(User.phone == phone)
    elif email:
        query = query.where(User.email == email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        user = User(phone=phone, email=email, full_name=full_name, is_verified=True)
        db.add(user)
        await db.flush()
        # Create empty profile
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        await db.flush()

    return user


def _token_response(user: User, profile: UserProfile | None) -> TokenResponse:
    uid = str(user.id)
    return TokenResponse(
        access_token=_create_access_token(uid),
        refresh_token=_create_refresh_token(uid),
        user_id=uid,
        is_onboarded=bool(profile and profile.is_onboarded),
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/send-otp", status_code=200)
async def send_otp(body: SendOtpRequest) -> dict:
    from services.otp import create_and_send_otp, otp_exists

    # Prevent spam: block if OTP already sent within TTL window
    if await otp_exists(body.phone):
        raise HTTPException(
            status_code=429,
            detail="OTP already sent. Wait 10 minutes before requesting again.",
        )

    dev_otp = await create_and_send_otp(body.phone, debug=settings.debug)
    return {"message": "OTP sent", "dev_otp": dev_otp}


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp_endpoint(body: VerifyOtpRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    from services.otp import verify_otp as redis_verify_otp

    valid = await redis_verify_otp(body.phone, body.otp)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user = await _get_or_create_user(db, phone=body.phone)
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()
    return _token_response(user, profile)


@router.post("/google", response_model=TokenResponse)
async def google_auth(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    # TODO: verify id_token with Google in production
    user = await _get_or_create_user(db, email=str(body.email), full_name=body.full_name)

    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()

    return _token_response(user, profile)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        payload = jwt.decode(body.refresh_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    profile = result.scalar_one_or_none()

    return _token_response(user, profile)


@router.post("/logout", status_code=200)
async def logout() -> dict:
    # In production: add refresh token to Redis blocklist
    return {"message": "Logged out"}
