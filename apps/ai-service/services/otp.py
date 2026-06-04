"""
OTP service — Redis-backed storage + MSG91 SMS delivery.

Redis key: otp:{phone}  →  hashed OTP string, TTL = 10 minutes
On verify: key is deleted (one-time use).

MSG91 API: https://docs.msg91.com/reference/send-otp
"""
from __future__ import annotations

import hashlib
import logging
import random
import string

import httpx
import redis.asyncio as aioredis

from config import settings

log = logging.getLogger(__name__)

OTP_TTL_SECONDS = 600  # 10 minutes
OTP_LENGTH = 6
OTP_KEY_PREFIX = "otp:"


# ─── Redis client ─────────────────────────────────────────────────────────────

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


# ─── OTP helpers ─────────────────────────────────────────────────────────────

def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=OTP_LENGTH))


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


# ─── Store / verify ───────────────────────────────────────────────────────────

async def store_otp(phone: str, otp: str) -> None:
    """Store hashed OTP in Redis with TTL."""
    redis = get_redis()
    key = f"{OTP_KEY_PREFIX}{phone}"
    await redis.setex(key, OTP_TTL_SECONDS, _hash_otp(otp))


async def verify_otp(phone: str, otp: str) -> bool:
    """
    Verify OTP. Returns True if valid.
    Deletes the key on success (one-time use).
    """
    redis = get_redis()
    key = f"{OTP_KEY_PREFIX}{phone}"
    stored_hash = await redis.get(key)

    if not stored_hash:
        return False

    if stored_hash != _hash_otp(otp):
        return False

    await redis.delete(key)  # invalidate immediately
    return True


async def otp_exists(phone: str) -> bool:
    """Check if an OTP was already sent (to avoid spam)."""
    redis = get_redis()
    return bool(await redis.exists(f"{OTP_KEY_PREFIX}{phone}"))


# ─── SMS delivery (MSG91) ─────────────────────────────────────────────────────

async def send_otp_sms(phone: str, otp: str) -> bool:
    """
    Send OTP via MSG91 (India-optimised SMS, DLT compliant).
    Falls back to logging if API key not configured.
    """
    if not settings.msg91_auth_key:
        log.warning("[DEV] OTP for %s: %s", phone, otp)
        return False

    # MSG91 Send OTP API
    payload = {
        "template_id": settings.msg91_otp_template_id,
        "mobile":      f"91{phone}" if not phone.startswith("91") else phone,
        "authkey":     settings.msg91_auth_key,
        "otp":         otp,
        "sender":      settings.msg91_sender_id,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.msg91.com/api/v5/otp",
                json=payload,
                timeout=10,
            )
            data = resp.json()
            if data.get("type") == "success":
                log.info("OTP sent via MSG91 to %s", phone)
                return True
            log.error("MSG91 error: %s", data)
            return False
    except Exception as e:
        log.error("MSG91 request failed: %s", e)
        return False


# ─── Combined: generate + store + send ───────────────────────────────────────

async def create_and_send_otp(phone: str, debug: bool = False) -> str | None:
    """
    Generate OTP, store in Redis, send via MSG91.
    Returns the OTP if debug=True (for dev/test), else None.
    """
    otp = _generate_otp()
    await store_otp(phone, otp)
    await send_otp_sms(phone, otp)
    return otp if debug else None
