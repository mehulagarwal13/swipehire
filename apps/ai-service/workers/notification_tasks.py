"""
Notification and email sync Celery tasks.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import settings
from models.user import User
from workers.celery_app import app

log = logging.getLogger(__name__)


def _make_session():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False), engine


@app.task(
    queue="default",
    name="workers.notification_tasks.sync_all_email_statuses",
    time_limit=600,
)
def sync_all_email_statuses() -> dict:
    return asyncio.get_event_loop().run_until_complete(_sync_all_async())


async def _sync_all_async() -> dict:
    from services.email_sync import sync_applications_from_gmail

    session_factory, engine = _make_session()
    total_updated = 0

    async with session_factory() as db:
        # Only sync users who have Gmail connected
        result = await db.execute(
            select(User.id).where(User.is_active == True)
        )
        user_ids = [str(row[0]) for row in result.all()]

    for user_id in user_ids:
        try:
            async with session_factory() as db:
                summary = await sync_applications_from_gmail(user_id, db)
                updated = summary.get("updated", 0)
                total_updated += updated

                # Send notification if status changed
                if updated > 0:
                    for change in summary.get("changes", []):
                        await _send_status_change_notification(user_id, change, db)

        except Exception as e:
            log.warning("Email sync failed for user %s: %s", user_id, e)

    await engine.dispose()
    return {"users_checked": len(user_ids), "total_updates": total_updated}


async def _send_status_change_notification(user_id: str, change: dict, db) -> None:
    from services.notifications import notify, NotificationPayload, NotificationType
    from models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    payload = NotificationPayload(
        user_id=user_id,
        type=NotificationType.STATUS_CHANGE,
        phone=user.phone,
        email=user.email,
        full_name=user.full_name or "",
        data={
            "role":       change.get("job", ""),
            "company":    change.get("company", ""),
            "new_status": change.get("new_status", "").replace("_", " ").title(),
        },
    )
    await notify(payload)


@app.task(
    queue="default",
    name="workers.notification_tasks.send_daily_match_digest",
)
def send_daily_match_digest() -> dict:
    """Send daily digest of top job matches to all active users."""
    return asyncio.get_event_loop().run_until_complete(_send_digest_async())


async def _send_digest_async() -> dict:
    from services.notifications import notify, NotificationPayload, NotificationType
    from sqlalchemy import text

    session_factory, engine = _make_session()
    sent = 0

    async with session_factory() as db:
        # Find users with 5+ new matches >= 85 score in the last 24h
        result = await db.execute(text("""
            SELECT u.id, u.phone, u.email, u.full_name, COUNT(*) as match_count
            FROM users u
            JOIN job_match_scores jms ON jms.user_id = u.id
            JOIN jobs j ON j.id = jms.job_id
            LEFT JOIN swipes s ON s.user_id = u.id AND s.job_id = j.id
            WHERE jms.score >= 85
              AND jms.computed_at >= NOW() - INTERVAL '24 hours'
              AND s.id IS NULL
              AND u.is_active = true
            GROUP BY u.id, u.phone, u.email, u.full_name
            HAVING COUNT(*) >= 5
        """))
        users_with_matches = result.all()

    for row in users_with_matches:
        try:
            payload = NotificationPayload(
                user_id=str(row.id),
                type=NotificationType.NEW_MATCHES,
                phone=row.phone,
                email=row.email,
                full_name=row.full_name or "",
                data={"count": row.match_count},
            )
            async with session_factory() as db:
                await notify(payload)
            sent += 1
        except Exception as e:
            log.warning("Digest notification failed for user %s: %s", row.id, e)

    await engine.dispose()
    return {"digests_sent": sent}
