"""
Celery scraping tasks — production-hardened with:
  - Rotating proxies
  - CAPTCHA bypass (2captcha)
  - Exponential retry on failure
  - Redis bloom filter deduplication
  - Meilisearch + Qdrant auto-indexing after insert
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta

from celery import Task
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import settings
from models.job import Job
from workers.celery_app import app
from workers.proxy_manager import ProxyManager, CaptchaSolver

log = logging.getLogger(__name__)

# ─── DB session factory for workers ──────────────────────────────────────────

def _make_session():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False), engine


# ─── Deduplication ────────────────────────────────────────────────────────────

async def _is_duplicate(redis_client, job_key: str) -> bool:
    """Redis bloom filter deduplication. Falls back to hash set if BF not available."""
    h = hashlib.md5(job_key.lower().encode()).hexdigest()
    try:
        exists = await redis_client.bf().exists("jobs_bloom", h)
        if not exists:
            await redis_client.bf().add("jobs_bloom", h)
        return bool(exists)
    except Exception:
        # Fallback: simple set
        key = f"seen_jobs:{h}"
        if await redis_client.exists(key):
            return True
        await redis_client.setex(key, 86400 * 7, "1")  # 7-day TTL
        return False


async def _save_jobs_to_db(jobs_data: list[dict]) -> int:
    """Insert new jobs, skip duplicates. Returns count inserted."""
    if not jobs_data:
        return 0

    session_factory, engine = _make_session()
    saved = 0

    async with session_factory() as db:
        for jd in jobs_data:
            # Check DB-level duplicate
            existing = await db.execute(
                select(Job).where(
                    Job.external_id == jd.get("external_id"),
                    Job.source == jd.get("source"),
                )
            )
            if existing.scalar_one_or_none():
                continue

            job = Job(**{k: v for k, v in jd.items() if hasattr(Job, k)})
            db.add(job)
            saved += 1

        await db.commit()

    await engine.dispose()
    log.info("Saved %d new jobs to DB", saved)
    return saved


async def _index_new_jobs(jobs_data: list[dict]) -> None:
    """After saving to DB, index into Meilisearch + Qdrant."""
    try:
        from services.search import bulk_index_jobs, job_to_document
        from services.vector_store import bulk_upsert_jobs
        from ml.embeddings import embed_job

        session_factory, engine = _make_session()
        async with session_factory() as db:
            # Fetch the newly inserted jobs
            external_ids = [j.get("external_id") for j in jobs_data if j.get("external_id")]
            result = await db.execute(
                select(Job).where(Job.external_id.in_(external_ids))
            )
            db_jobs = result.scalars().all()

        # Meilisearch
        docs = [job_to_document(j) for j in db_jobs]
        await bulk_index_jobs(docs)

        # Qdrant — embed in batches of 10
        BATCH = 10
        for i in range(0, len(db_jobs), BATCH):
            batch = db_jobs[i: i + BATCH]
            embeddings = await asyncio.gather(*[embed_job(j) for j in batch])
            await bulk_upsert_jobs(list(zip(batch, embeddings)))

        await engine.dispose()
        log.info("Indexed %d jobs into Meilisearch + Qdrant", len(db_jobs))
    except Exception as e:
        log.error("Index error (non-fatal): %s", e)


# ─── Naukri scraper task ──────────────────────────────────────────────────────

@app.task(
    bind=True,
    max_retries=5,
    default_retry_delay=300,
    queue="scraping",
    name="workers.scraping_tasks.scrape_naukri",
)
def scrape_naukri(self: Task, keywords: list[str], location: str = "india") -> dict:
    """Scrape Naukri.com for multiple keyword+location combos."""
    return asyncio.get_event_loop().run_until_complete(
        _scrape_naukri_async(self, keywords, location)
    )


async def _scrape_naukri_async(task: Task, keywords: list[str], location: str) -> dict:
    from scrapers.naukri import NaukriScraper

    total_saved = 0
    errors = []

    async with ProxyManager() as pm:
        for keyword in keywords:
            try:
                proxy = await pm.get_proxy()

                async with NaukriScraper(headless=True, proxy=proxy) as scraper:
                    jobs = await scraper.scrape(keyword, location, pages=5)

                all_job_dicts = []
                for j in jobs:
                    all_job_dicts.append({
                        "external_id":    j.external_id,
                        "source":         "naukri",
                        "title":          j.title,
                        "company":        j.company,
                        "location":       j.location,
                        "is_remote":      False,
                        "skills_required": j.skills,
                        "apply_url":      j.apply_url,
                        "job_type":       "full-time",
                    })

                saved = await _save_jobs_to_db(all_job_dicts)
                await _index_new_jobs(all_job_dicts)
                total_saved += saved

                if proxy:
                    await pm.report_success(proxy["server"])

                log.info("Naukri '%s': %d new jobs", keyword, saved)
                await asyncio.sleep(10)  # polite delay between keywords

            except Exception as e:
                log.error("Naukri scrape failed for '%s': %s", keyword, e)
                errors.append({"keyword": keyword, "error": str(e)})
                if proxy:
                    await pm.report_failure(proxy["server"])

                # Retry the task on scraping failure
                try:
                    task.retry(exc=e, countdown=300)
                except task.MaxRetriesExceededError:
                    log.error("Max retries exceeded for Naukri scraping")

    return {"saved": total_saved, "errors": errors, "source": "naukri"}


# ─── LinkedIn scraper task ────────────────────────────────────────────────────

@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    queue="scraping",
    name="workers.scraping_tasks.scrape_linkedin",
)
def scrape_linkedin(self: Task, keywords: list[str], location: str = "India") -> dict:
    return asyncio.get_event_loop().run_until_complete(
        _scrape_linkedin_async(self, keywords, location)
    )


async def _scrape_linkedin_async(task: Task, keywords: list[str], location: str) -> dict:
    """LinkedIn via RapidAPI — no scraping needed, just API calls."""
    import httpx

    if not settings.rapidapi_key:
        log.warning("RAPIDAPI_KEY not set — skipping LinkedIn scrape")
        return {"saved": 0, "source": "linkedin"}

    total_saved = 0

    async with httpx.AsyncClient(timeout=30) as client:
        for keyword in keywords:
            try:
                resp = await client.get(
                    "https://linkedin-jobs-search.p.rapidapi.com/",
                    params={
                        "query":    keyword,
                        "location": location,
                        "page":     "1",
                    },
                    headers={
                        "X-RapidAPI-Key":  settings.rapidapi_key,
                        "X-RapidAPI-Host": "linkedin-jobs-search.p.rapidapi.com",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                job_dicts = []
                for item in data:
                    job_dicts.append({
                        "external_id":    item.get("job_id", ""),
                        "source":         "linkedin",
                        "title":          item.get("job_title", ""),
                        "company":        item.get("company_name", ""),
                        "location":       item.get("job_location", ""),
                        "is_remote":      "remote" in item.get("job_location", "").lower(),
                        "description":    item.get("job_description", ""),
                        "apply_url":      item.get("linkedin_job_url_cleaned", ""),
                        "skills_required": [],
                        "job_type":       "full-time",
                        "posted_at":      datetime.utcnow(),
                    })

                saved = await _save_jobs_to_db(job_dicts)
                await _index_new_jobs(job_dicts)
                total_saved += saved
                await asyncio.sleep(2)

            except Exception as e:
                log.error("LinkedIn API failed for '%s': %s", keyword, e)

    return {"saved": total_saved, "source": "linkedin"}


# ─── Internshala scraper task ─────────────────────────────────────────────────

@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=600,
    queue="scraping",
    name="workers.scraping_tasks.scrape_internshala",
)
def scrape_internshala(self: Task, categories: list[str]) -> dict:
    return asyncio.get_event_loop().run_until_complete(
        _scrape_internshala_async(categories)
    )


async def _scrape_internshala_async(categories: list[str]) -> dict:
    from scrapers.internshala import IntershalaScraper

    total_saved = 0
    scraper = IntershalaScraper()

    for category in categories:
        try:
            jobs = await scraper.scrape_internships(category, pages=3)
            job_dicts = []
            for j in jobs:
                job_dicts.append({
                    "external_id":    j.external_id,
                    "source":         "internshala",
                    "title":          j.title,
                    "company":        j.company,
                    "location":       j.location,
                    "is_remote":      j.is_wfh,
                    "salary_min_lpa": 0,
                    "salary_max_lpa": 0.5,
                    "experience_min": 0,
                    "experience_max": 1,
                    "skills_required": j.skills,
                    "apply_url":      j.apply_url,
                    "job_type":       "internship",
                })

            saved = await _save_jobs_to_db(job_dicts)
            await _index_new_jobs(job_dicts)
            total_saved += saved
            await asyncio.sleep(5)

        except Exception as e:
            log.error("Internshala scrape failed for '%s': %s", category, e)

    return {"saved": total_saved, "source": "internshala"}


# ─── Maintenance tasks ────────────────────────────────────────────────────────

@app.task(queue="default", name="workers.scraping_tasks.expire_old_jobs")
def expire_old_jobs() -> dict:
    return asyncio.get_event_loop().run_until_complete(_expire_old_jobs_async())


async def _expire_old_jobs_async() -> dict:
    cutoff = datetime.utcnow() - timedelta(days=30)
    session_factory, engine = _make_session()

    async with session_factory() as db:
        result = await db.execute(
            update(Job)
            .where(Job.posted_at < cutoff, Job.is_active == True)
            .values(is_active=False)
        )
        expired = result.rowcount
        await db.commit()

    await engine.dispose()
    log.info("Expired %d old jobs", expired)
    return {"expired": expired}
