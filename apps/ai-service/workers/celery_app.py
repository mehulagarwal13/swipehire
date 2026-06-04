"""
Celery application — job scraping, match scoring, and auto-apply workers.

Start workers:
  celery -A workers.celery_app worker --loglevel=info --concurrency=4

Start beat scheduler (cron jobs):
  celery -A workers.celery_app beat --loglevel=info

Worker queues:
  scraping   — CPU-light, high I/O  (web scraping)
  ml         — CPU-heavy            (embedding + match scoring)
  apply      — isolated containers  (Playwright auto-apply)
  default    — general tasks
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from config import settings

app = Celery(
    "swipehire",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "workers.scraping_tasks",
        "workers.scoring_tasks",
        "workers.apply_tasks",
        "workers.notification_tasks",
    ],
)

# ─── Serialization ────────────────────────────────────────────────────────────
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,           # re-queue on worker crash
    worker_prefetch_multiplier=1,  # fair distribution
    task_reject_on_worker_lost=True,
)

# ─── Queues ───────────────────────────────────────────────────────────────────
default_exchange = Exchange("default", type="direct")
app.conf.task_queues = (
    Queue("default",  default_exchange, routing_key="default"),
    Queue("scraping", default_exchange, routing_key="scraping"),
    Queue("ml",       default_exchange, routing_key="ml"),
    Queue("apply",    default_exchange, routing_key="apply"),
)
app.conf.task_default_queue = "default"
app.conf.task_routes = {
    "workers.scraping_tasks.*":      {"queue": "scraping"},
    "workers.scoring_tasks.*":       {"queue": "ml"},
    "workers.apply_tasks.*":         {"queue": "apply"},
    "workers.notification_tasks.*":  {"queue": "default"},
}

# ─── Retry defaults ───────────────────────────────────────────────────────────
app.conf.task_annotations = {
    "*": {
        "max_retries": 3,
        "default_retry_delay": 60,   # 1 minute between retries
    },
    "workers.scraping_tasks.*": {
        "max_retries": 5,
        "default_retry_delay": 300,  # 5 minutes (rate limiting)
    },
}

# ─── Beat schedule (cron) ─────────────────────────────────────────────────────
app.conf.beat_schedule = {
    # Naukri: every 6 hours
    "scrape-naukri-6h": {
        "task": "workers.scraping_tasks.scrape_naukri",
        "schedule": crontab(minute=0, hour="*/6"),
        "args": (["python developer", "react developer", "data engineer",
                  "machine learning", "devops", "android developer"], "india"),
    },
    # LinkedIn (via RapidAPI): every 2 hours
    "scrape-linkedin-2h": {
        "task": "workers.scraping_tasks.scrape_linkedin",
        "schedule": crontab(minute=30, hour="*/2"),
        "args": (["software engineer", "full stack", "backend developer"], "India"),
    },
    # Internshala: every 12 hours
    "scrape-internshala-12h": {
        "task": "workers.scraping_tasks.scrape_internshala",
        "schedule": crontab(minute=0, hour="*/12"),
        "args": (["computer-science", "software-development", "data-science"],),
    },
    # Recompute match scores for active users every night at 2 AM IST
    "recompute-match-scores-nightly": {
        "task": "workers.scoring_tasks.recompute_all_match_scores",
        "schedule": crontab(minute=0, hour=2),
    },
    # Email status sync every 30 minutes
    "sync-application-statuses-30m": {
        "task": "workers.notification_tasks.sync_all_email_statuses",
        "schedule": crontab(minute="*/30"),
    },
    # Expire old jobs (>30 days) every day at 3 AM IST
    "expire-old-jobs-daily": {
        "task": "workers.scraping_tasks.expire_old_jobs",
        "schedule": crontab(minute=0, hour=3),
    },
}
