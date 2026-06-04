"""
One-time script: embed all jobs in PostgreSQL and push to Qdrant.
Run after seeding: python scripts/index_jobs_qdrant.py

Progress is printed every 10 jobs. Safe to re-run (upserts are idempotent).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow imports from parent dir
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config import settings
from ml.embeddings import embed_job
from models.job import Job
from services.vector_store import ensure_collections, bulk_upsert_jobs


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    await ensure_collections()
    print("✅ Qdrant collections ready")

    async with session_factory() as db:
        result = await db.execute(select(Job).where(Job.is_active == True))
        jobs = result.scalars().all()

    print(f"Embedding {len(jobs)} jobs…")

    BATCH = 20
    total = 0
    for i in range(0, len(jobs), BATCH):
        batch = list(jobs[i: i + BATCH])
        embeddings = await asyncio.gather(*[embed_job(j) for j in batch])
        await bulk_upsert_jobs(list(zip(batch, embeddings)))
        total += len(batch)
        print(f"  {total}/{len(jobs)} indexed")

    await engine.dispose()
    print(f"✅ Done — {total} jobs indexed in Qdrant")


if __name__ == "__main__":
    asyncio.run(main())
