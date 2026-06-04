"""
Razorpay subscription routes (India payments).
POST /payments/create-subscription → create Razorpay subscription
POST /payments/webhook             → handle Razorpay webhook events
GET  /payments/plans               → return plan pricing
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models.user import User
from routers.deps import get_current_user

log = logging.getLogger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])

# ─── Plan config ─────────────────────────────────────────────────────────────

PLANS = {
    "pro": {
        "name": "Pro",
        "price_inr": 299,
        "features": [
            "Unlimited swipes",
            "Auto-apply on 10 portals",
            "Detailed score breakdown",
            "Priority job feed",
            "WhatsApp notifications",
        ],
        "razorpay_plan_id": "plan_pro_monthly",  # set in Razorpay dashboard
    },
    "premium": {
        "name": "Premium",
        "price_inr": 699,
        "features": [
            "Everything in Pro",
            "Resume AI rewrite per job",
            "Interview prep AI",
            "Salary negotiation insights",
            "Dedicated application manager",
        ],
        "razorpay_plan_id": "plan_premium_monthly",
    },
}


# ─── Schemas ─────────────────────────────────────────────────────────────────

class CreateSubscriptionRequest(BaseModel):
    plan: str  # "pro" | "premium"


class SubscriptionResponse(BaseModel):
    subscription_id: str
    razorpay_key_id: str
    plan: str
    amount: int


# ─── Razorpay client ─────────────────────────────────────────────────────────

async def _razorpay_post(endpoint: str, payload: dict) -> dict:
    async with httpx.AsyncClient(
        auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
        base_url="https://api.razorpay.com/v1",
    ) as client:
        resp = await client.post(endpoint, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("/plans")
async def get_plans() -> dict:
    return {"plans": PLANS}


@router.post("/create-subscription", response_model=SubscriptionResponse)
async def create_subscription(
    body: CreateSubscriptionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> SubscriptionResponse:
    if body.plan not in PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {body.plan}")

    plan_config = PLANS[body.plan]

    try:
        sub = await _razorpay_post(
            "/subscriptions",
            {
                "plan_id":       plan_config["razorpay_plan_id"],
                "total_count":   12,  # 12 months
                "quantity":      1,
                "customer_notify": 1,
                "notes": {
                    "user_id": str(current_user.id),
                    "plan":    body.plan,
                },
            },
        )
    except Exception as e:
        log.error("Razorpay subscription creation failed: %s", e)
        raise HTTPException(status_code=502, detail="Payment gateway error") from e

    return SubscriptionResponse(
        subscription_id=sub["id"],
        razorpay_key_id=settings.razorpay_key_id,
        plan=body.plan,
        amount=plan_config["price_inr"] * 100,  # paise
    )


@router.post("/webhook", status_code=200)
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_razorpay_signature: str = Header(None),
) -> dict:
    body_bytes = await request.body()

    # Verify webhook signature
    expected = hmac.HMAC(
        settings.razorpay_webhook_secret.encode(),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()

    if x_razorpay_signature != expected:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event = json.loads(body_bytes)
    event_type = event.get("event", "")
    log.info("Razorpay webhook: %s", event_type)

    if event_type == "subscription.activated":
        payload = event["payload"]["subscription"]["entity"]
        user_id = payload.get("notes", {}).get("user_id")
        plan    = payload.get("notes", {}).get("plan", "pro")

        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.plan = plan
                await db.commit()
                log.info("User %s upgraded to %s", user_id, plan)

    elif event_type in ("subscription.cancelled", "subscription.completed"):
        payload = event["payload"]["subscription"]["entity"]
        user_id = payload.get("notes", {}).get("user_id")
        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.plan = "free"
                await db.commit()

    return {"status": "ok"}
