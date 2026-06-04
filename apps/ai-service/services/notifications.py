"""
Notification service — sends WhatsApp + Email alerts.

Triggers:
  - new_matches     → 5+ jobs ≥85% match found today
  - app_viewed      → recruiter viewed application
  - interview_invite → interview scheduled
  - offer_received  → offer extended
  - status_change   → any application status update

WhatsApp: Meta Cloud API (pre-approved templates required)
Email:    Resend.com transactional email
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

import httpx

from config import settings

log = logging.getLogger(__name__)


class NotificationType(str, Enum):
    NEW_MATCHES    = "new_matches"
    APP_VIEWED     = "app_viewed"
    INTERVIEW      = "interview_invite"
    OFFER          = "offer_received"
    STATUS_CHANGE  = "status_change"


@dataclass
class NotificationPayload:
    user_id: str
    type: NotificationType
    phone: str | None        # +91XXXXXXXXXX
    email: str | None
    full_name: str
    data: dict               # template-specific variables


# ─── WhatsApp (Meta Cloud API) ────────────────────────────────────────────────

_WA_TEMPLATES: dict[NotificationType, str] = {
    NotificationType.NEW_MATCHES:   "new_job_matches",
    NotificationType.APP_VIEWED:    "application_viewed",
    NotificationType.INTERVIEW:     "interview_invite",
    NotificationType.OFFER:         "offer_received",
    NotificationType.STATUS_CHANGE: "status_update",
}

_WA_BODY_VARS: dict[NotificationType, list[str]] = {
    NotificationType.NEW_MATCHES:   ["{{1}}", "{{2}}"],  # count, cta_url
    NotificationType.APP_VIEWED:    ["{{1}}", "{{2}}"],  # company, role
    NotificationType.INTERVIEW:     ["{{1}}", "{{2}}"],  # company, date
    NotificationType.OFFER:         ["{{1}}", "{{2}}"],  # company, amount
    NotificationType.STATUS_CHANGE: ["{{1}}", "{{2}}", "{{3}}"],  # role, company, new_status
}


async def send_whatsapp(payload: NotificationPayload) -> bool:
    if not payload.phone or not settings.whatsapp_access_token:
        log.debug("WhatsApp skipped — no phone or token")
        return False

    template_name = _WA_TEMPLATES[payload.type]

    # Build parameter values from payload.data
    params = []
    if payload.type == NotificationType.NEW_MATCHES:
        params = [str(payload.data.get("count", 0)), "https://swipehire.in/swipe"]
    elif payload.type == NotificationType.APP_VIEWED:
        params = [payload.data.get("company", ""), payload.data.get("role", "")]
    elif payload.type == NotificationType.INTERVIEW:
        params = [payload.data.get("company", ""), payload.data.get("date", "")]
    elif payload.type == NotificationType.OFFER:
        params = [payload.data.get("company", ""), str(payload.data.get("amount", ""))]
    elif payload.type == NotificationType.STATUS_CHANGE:
        params = [
            payload.data.get("role", ""),
            payload.data.get("company", ""),
            payload.data.get("new_status", "").replace("_", " ").title(),
        ]

    body = {
        "messaging_product": "whatsapp",
        "to": payload.phone if payload.phone.startswith("+") else f"+91{payload.phone}",
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en_IN"},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": p} for p in params],
                }
            ],
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://graph.facebook.com/v18.0/{settings.whatsapp_phone_number_id}/messages",
                headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
                json=body,
                timeout=10,
            )
            resp.raise_for_status()
            log.info("WhatsApp sent: %s to %s", template_name, payload.phone)
            return True
    except Exception as e:
        log.error("WhatsApp send failed: %s", e)
        return False


# ─── Email (Resend) ───────────────────────────────────────────────────────────

_EMAIL_SUBJECTS: dict[NotificationType, str] = {
    NotificationType.NEW_MATCHES:   "🎯 {count} new jobs match your profile today",
    NotificationType.APP_VIEWED:    "👁️ {company} viewed your application for {role}",
    NotificationType.INTERVIEW:     "🎉 Interview scheduled at {company}",
    NotificationType.OFFER:         "🎊 Offer received from {company}!",
    NotificationType.STATUS_CHANGE: "📋 Application update: {role} at {company}",
}


def _build_email_html(payload: NotificationPayload) -> str:
    d = payload.data
    name = payload.full_name.split()[0] if payload.full_name else "there"

    if payload.type == NotificationType.NEW_MATCHES:
        headline = f"🎯 {d.get('count', 0)} New Job Matches"
        body = f"Hi {name}, you have <strong>{d.get('count', 0)} new jobs</strong> matching 85%+ today. Jump in and swipe!"
        cta = ("View Matches", "https://swipehire.in/swipe")

    elif payload.type == NotificationType.INTERVIEW:
        headline = "🎉 Interview Scheduled!"
        body = f"Hi {name}, <strong>{d.get('company', '')}</strong> has scheduled an interview for the <strong>{d.get('role', '')}</strong> role on <strong>{d.get('date', '')}</strong>."
        cta = ("View Application", f"https://swipehire.in/applications")

    elif payload.type == NotificationType.OFFER:
        headline = "🎊 You Got an Offer!"
        body = f"Congratulations {name}! <strong>{d.get('company', '')}</strong> has extended an offer of <strong>₹{d.get('amount', '')} LPA</strong> for {d.get('role', '')}."
        cta = ("View Offer", "https://swipehire.in/applications")

    else:
        headline = "SwipeHire Update"
        body = f"Hi {name}, there's an update on your application for <strong>{d.get('role', '')}</strong> at <strong>{d.get('company', '')}</strong>."
        cta = ("View Applications", "https://swipehire.in/applications")

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f9fafb; margin: 0; padding: 32px 16px;">
  <div style="max-width: 520px; margin: 0 auto; background: white; border-radius: 20px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08);">
    <div style="background: linear-gradient(135deg, #16a34a, #22c55e); padding: 32px; text-align: center;">
      <h1 style="color: white; font-size: 24px; margin: 0; font-weight: 800;">⚡ SwipeHire</h1>
    </div>
    <div style="padding: 32px;">
      <h2 style="color: #111827; font-size: 20px; margin: 0 0 12px;">{headline}</h2>
      <p style="color: #6b7280; font-size: 15px; line-height: 1.6; margin: 0 0 24px;">{body}</p>
      <a href="{cta[1]}" style="display: inline-block; background: #16a34a; color: white; padding: 14px 28px; border-radius: 12px; text-decoration: none; font-weight: 600; font-size: 15px;">{cta[0]}</a>
    </div>
    <div style="padding: 16px 32px; border-top: 1px solid #f3f4f6; text-align: center;">
      <p style="color: #9ca3af; font-size: 12px; margin: 0;">
        SwipeHire · India's AI Job Platform · <a href="https://swipehire.in/unsubscribe" style="color: #9ca3af;">Unsubscribe</a>
      </p>
    </div>
  </div>
</body>
</html>
"""


async def send_email(payload: NotificationPayload) -> bool:
    if not payload.email or not settings.resend_api_key:
        return False

    d = payload.data
    subject_template = _EMAIL_SUBJECTS[payload.type]
    subject = subject_template.format(**d, name=payload.full_name)
    html = _build_email_html(payload)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": "SwipeHire <noreply@swipehire.in>",
                    "to": [payload.email],
                    "subject": subject,
                    "html": html,
                },
                timeout=10,
            )
            resp.raise_for_status()
            log.info("Email sent: %s to %s", payload.type, payload.email)
            return True
    except Exception as e:
        log.error("Email send failed: %s", e)
        return False


# ─── Unified dispatcher ───────────────────────────────────────────────────────

async def _send_push_for_payload(payload: NotificationPayload) -> bool:
    """Fetch user's push token from DB and send push notification."""
    try:
        import redis.asyncio as aioredis
        from config import settings
        from services.push_notifications import (
            push_new_matches, push_interview_scheduled,
            push_offer_received, push_status_change,
        )

        # Get push token from Redis cache or DB
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        token = await redis.get(f"push_token:{payload.user_id}")

        if not token:
            return False

        d = payload.data
        if payload.type == NotificationType.NEW_MATCHES:
            return await push_new_matches(token, d.get("count", 0))
        elif payload.type == NotificationType.INTERVIEW:
            return await push_interview_scheduled(token, d.get("company", ""), d.get("date", ""))
        elif payload.type == NotificationType.OFFER:
            return await push_offer_received(token, d.get("company", ""), d.get("role", ""))
        elif payload.type == NotificationType.STATUS_CHANGE:
            return await push_status_change(token, d.get("company", ""), d.get("role", ""), d.get("new_status", ""))
        return False
    except Exception as e:
        log.debug("Push notification failed: %s", e)
        return False


async def notify(payload: NotificationPayload) -> dict[str, bool]:
    """Send WhatsApp, Email, and Push notifications. Returns channel results."""
    wa, em, push = await asyncio.gather(
        send_whatsapp(payload),
        send_email(payload),
        _send_push_for_payload(payload),
    )
    return {"whatsapp": wa, "email": em, "push": push}


import asyncio  # noqa: E402  (imported at end to avoid circular issues in type hints)


# ─── Config additions (add to config.py) ─────────────────────────────────────
# These need to be added to the Settings class in config.py:
#
#   resend_api_key: str = ""
#   whatsapp_phone_number_id: str = ""
#   whatsapp_access_token: str = ""
