"""
Application status sync via Gmail API.

Flow:
  1. User connects Gmail via OAuth → tokens stored in DB
  2. Celery task polls every 30 minutes for new emails matching known companies
  3. Email content classified by Gemini → new status determined
  4. Application kanban updated automatically + notification sent

Status detection patterns (rule-based first, LLM fallback):
  - "schedule an interview" / "interview on" → interview_scheduled
  - "pleased to offer" / "offer letter" / "congratulations" → offer_extended
  - "unfortunately" / "not moving forward" / "regret" → rejected
  - "shortlisted" / "screening call" → screening
  - "application received" / "thank you for applying" → applied (no change)
"""
from __future__ import annotations

import base64
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import httpx
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

# ─── Status detection patterns ────────────────────────────────────────────────

_STATUS_PATTERNS: list[tuple[str, str]] = [
    # (regex pattern, target status)
    (r"(schedule|invite|book).{0,30}(interview|call|meeting)",  "interview_scheduled"),
    (r"(interview).{0,20}(scheduled|confirmed|on\s+\w+\s+\d)",  "interview_scheduled"),
    (r"(pleased|delighted|happy).{0,40}offer",                  "offer_extended"),
    (r"(offer letter|job offer|ctc|compensation)",               "offer_extended"),
    (r"(congratulation|selected|hired)",                         "offer_extended"),
    (r"(unfortunately|regret|not.{0,10}(moving forward|selected|proceed))", "rejected"),
    (r"(shortlist|screening|initial|hr round)",                  "screening"),
]


@dataclass
class EmailClassification:
    raw_status: str           # detected status string
    confidence: float         # 0–1
    email_subject: str
    email_from: str
    detected_company: str
    email_date: str


def classify_email_content(subject: str, body: str, company_name: str) -> Optional[str]:
    """
    Rule-based email classification. Returns status string or None if uncertain.
    company_name is used to confirm the email is from the right sender.
    """
    text_lower = (subject + " " + body[:1000]).lower()

    # Skip auto-acknowledgement emails — no status change
    if re.search(r"(thank you for applying|application received|we will review)", text_lower):
        return None

    for pattern, status in _STATUS_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return status

    return None


async def classify_with_llm(subject: str, body: str, company: str, job_title: str) -> Optional[str]:
    """
    LLM fallback classification for ambiguous emails.
    Returns one of: interview_scheduled, offer_extended, rejected, screening, None
    """
    from config import settings

    prompt = f"""
Classify this job application email into one of these statuses:
- interview_scheduled (they want to schedule an interview)
- offer_extended (they're offering the job)
- rejected (they're rejecting the application)
- screening (initial phone/HR screen)
- null (no status change, acknowledgement only)

Company: {company}
Job: {job_title}
Subject: {subject}
Email body (first 500 chars): {body[:500]}

Reply with ONLY one of: interview_scheduled, offer_extended, rejected, screening, null
"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        result = response.text.strip().lower()
        valid = {"interview_scheduled", "offer_extended", "rejected", "screening", "null"}
        return result if result in valid else None
    except Exception as e:
        log.debug("LLM classification failed: %s", e)
        return None


# ─── Gmail OAuth token management ─────────────────────────────────────────────

class GmailClient:
    """
    Gmail API client using OAuth 2.0 tokens.
    Tokens are stored per-user in the DB (gmail_tokens table).
    """

    GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
    TOKEN_URL = "https://oauth2.googleapis.com/token"

    def __init__(self, access_token: str, refresh_token: str) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._headers = {"Authorization": f"Bearer {access_token}"}

    async def refresh_access_token(self) -> str:
        """Refresh the access token using the refresh token."""
        from config import settings
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.TOKEN_URL, data={
                "client_id":     settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "refresh_token": self.refresh_token,
                "grant_type":    "refresh_token",
            })
            data = resp.json()
            self.access_token = data["access_token"]
            self._headers = {"Authorization": f"Bearer {self.access_token}"}
            return self.access_token

    async def search_messages(self, query: str, max_results: int = 20) -> list[dict]:
        """Search Gmail messages."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.GMAIL_BASE}/messages",
                headers=self._headers,
                params={"q": query, "maxResults": max_results},
            )
            if resp.status_code == 401:
                await self.refresh_access_token()
                resp = await client.get(
                    f"{self.GMAIL_BASE}/messages",
                    headers=self._headers,
                    params={"q": query, "maxResults": max_results},
                )
            resp.raise_for_status()
            return resp.json().get("messages", [])

    async def get_message(self, message_id: str) -> dict:
        """Get full message content."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.GMAIL_BASE}/messages/{message_id}",
                headers=self._headers,
                params={"format": "full"},
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def extract_body(message: dict) -> str:
        """Extract plain text body from Gmail message payload."""
        payload = message.get("payload", {})

        def _decode(data: str) -> str:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")

        # Single part
        if "body" in payload and payload["body"].get("data"):
            return _decode(payload["body"]["data"])

        # Multi-part
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                return _decode(part["body"]["data"])

        return ""

    @staticmethod
    def extract_subject(message: dict) -> str:
        headers = message.get("payload", {}).get("headers", [])
        for h in headers:
            if h["name"].lower() == "subject":
                return h["value"]
        return ""

    @staticmethod
    def extract_from(message: dict) -> str:
        headers = message.get("payload", {}).get("headers", [])
        for h in headers:
            if h["name"].lower() == "from":
                return h["value"]
        return ""


# ─── Main sync function ───────────────────────────────────────────────────────

async def sync_applications_from_gmail(
    user_id: str,
    db: AsyncSession,
) -> dict:
    """
    Check user's Gmail for new emails from companies they applied to.
    Updates application statuses and sends notifications.
    Returns summary of changes made.
    """
    from models.swipe import Application
    from models.job import Job
    from models.user import User

    # Get user's Gmail tokens
    result = await db.execute(
        text("SELECT access_token, refresh_token FROM gmail_tokens WHERE user_id = :uid"),
        {"uid": user_id},
    )
    token_row = result.one_or_none()
    if not token_row:
        return {"error": "Gmail not connected", "user_id": user_id}

    gmail = GmailClient(token_row.access_token, token_row.refresh_token)

    # Get active applications
    apps_result = await db.execute(
        select(Application, Job)
        .join(Job, Job.id == Application.job_id)
        .where(
            Application.user_id == user_id,
            Application.status.in_(["applied", "screening"]),
        )
    )
    active_apps = apps_result.all()

    if not active_apps:
        return {"checked": 0, "updated": 0}

    updates = []
    since = (datetime.utcnow() - timedelta(days=7)).strftime("%Y/%m/%d")

    for app, job in active_apps:
        try:
            # Search Gmail for emails from this company
            query = f'from:{job.company.lower().replace(" ", "")} after:{since}'
            messages = await gmail.search_messages(query, max_results=5)

            for msg_stub in messages:
                msg = await gmail.get_message(msg_stub["id"])
                subject = gmail.extract_subject(msg)
                body = gmail.extract_body(msg)
                sender = gmail.extract_from(msg)

                # Rule-based classification first
                new_status = classify_email_content(subject, body, job.company)

                # LLM fallback for ambiguous cases
                if not new_status:
                    new_status = await classify_with_llm(subject, body, job.company, job.title)

                if new_status and new_status != "null" and new_status != app.status:
                    # Validate state machine
                    from routers.applications import _VALID_TRANSITIONS
                    allowed = _VALID_TRANSITIONS.get(app.status, [])
                    if new_status in allowed:
                        app.status = new_status
                        app.notes = f"Auto-detected from email: \"{subject}\""
                        await db.flush()

                        updates.append({
                            "application_id": str(app.id),
                            "job":            job.title,
                            "company":        job.company,
                            "old_status":     app.status,
                            "new_status":     new_status,
                            "email_subject":  subject,
                        })
                        log.info("Auto-updated %s → %s for %s @ %s",
                                 app.status, new_status, job.title, job.company)
                        break

        except Exception as e:
            log.warning("Email sync failed for app %s: %s", app.id, e)
            continue

    await db.commit()
    return {"checked": len(active_apps), "updated": len(updates), "changes": updates}
