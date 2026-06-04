"""
Expo Push Notification service.

Expo's push API handles both iOS (APNs) and Android (FCM) transparently.
We store Expo push tokens per user in the `push_tokens` table and send
via the Expo Push API (https://exp.host/--/api/v2/push/send).

Trigger points:
  - New job matches ≥ 85 score
  - Interview scheduled
  - Offer received
  - Application status change
  - Daily digest (5+ new matches)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

log = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
EXPO_RECEIPT_URL = "https://exp.host/--/api/v2/push/getReceipts"

# Expo push token format: ExponentPushToken[xxxxxx]
_TOKEN_PREFIX = "ExponentPushToken["


@dataclass
class PushMessage:
    to: str                     # Expo push token
    title: str
    body: str
    data: dict | None = None    # extra payload sent to the app
    sound: str = "default"
    badge: int = 1
    channel_id: str = "default"  # Android notification channel


def is_valid_expo_token(token: str) -> bool:
    return token.startswith(_TOKEN_PREFIX) or token.startswith("ExpoPushToken[")


async def send_push(messages: list[PushMessage]) -> dict:
    """
    Send push notifications via Expo Push API.
    Batches up to 100 messages per request (Expo limit).
    Returns {success: int, failed: int, errors: list}.
    """
    if not messages:
        return {"success": 0, "failed": 0}

    total_success = 0
    total_failed = 0
    all_errors = []

    BATCH_SIZE = 100
    for i in range(0, len(messages), BATCH_SIZE):
        batch = messages[i: i + BATCH_SIZE]
        payload = [
            {
                "to":        msg.to,
                "title":     msg.title,
                "body":      msg.body,
                "data":      msg.data or {},
                "sound":     msg.sound,
                "badge":     msg.badge,
                "channelId": msg.channel_id,
            }
            for msg in batch
            if is_valid_expo_token(msg.to)
        ]

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    EXPO_PUSH_URL,
                    json=payload,
                    headers={
                        "Accept":        "application/json",
                        "Accept-Encoding": "gzip, deflate",
                        "Content-Type":  "application/json",
                    },
                )
                resp.raise_for_status()
                result = resp.json()

                for ticket in result.get("data", []):
                    if ticket.get("status") == "ok":
                        total_success += 1
                    else:
                        total_failed += 1
                        all_errors.append(ticket.get("message", "unknown error"))

        except Exception as e:
            log.error("Expo push batch failed: %s", e)
            total_failed += len(batch)
            all_errors.append(str(e))

    log.info("Push notifications: %d sent, %d failed", total_success, total_failed)
    return {"success": total_success, "failed": total_failed, "errors": all_errors}


async def send_push_to_user(
    push_token: str,
    title: str,
    body: str,
    data: dict | None = None,
    channel_id: str = "default",
) -> bool:
    """Convenience wrapper for single-user push."""
    if not push_token or not is_valid_expo_token(push_token):
        return False

    result = await send_push([
        PushMessage(to=push_token, title=title, body=body, data=data, channel_id=channel_id)
    ])
    return result["success"] > 0


# ─── Pre-built notification templates ────────────────────────────────────────

async def push_new_matches(push_token: str, count: int) -> bool:
    return await send_push_to_user(
        push_token,
        title="🎯 New Job Matches",
        body=f"You have {count} new jobs matching 85%+ today. Swipe now!",
        data={"screen": "swipe", "type": "new_matches"},
        channel_id="matches",
    )


async def push_interview_scheduled(push_token: str, company: str, date: str) -> bool:
    return await send_push_to_user(
        push_token,
        title="🎉 Interview Scheduled!",
        body=f"{company} has scheduled your interview for {date}",
        data={"screen": "applications", "type": "interview"},
        channel_id="applications",
    )


async def push_offer_received(push_token: str, company: str, role: str) -> bool:
    return await send_push_to_user(
        push_token,
        title="🎊 You Got an Offer!",
        body=f"{company} has extended an offer for {role}",
        data={"screen": "applications", "type": "offer"},
        channel_id="applications",
    )


async def push_status_change(push_token: str, company: str, role: str, new_status: str) -> bool:
    status_label = new_status.replace("_", " ").title()
    return await send_push_to_user(
        push_token,
        title="📋 Application Update",
        body=f"{role} at {company}: {status_label}",
        data={"screen": "applications", "type": "status_change"},
        channel_id="applications",
    )
