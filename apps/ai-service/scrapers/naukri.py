"""
Naukri.com scraper — uses Playwright headless browser.
Runs every 6 hours via cron / Celery beat.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime

from playwright.async_api import async_playwright, Page, Browser
from tenacity import retry, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)


@dataclass
class ScrapedJob:
    title: str
    company: str
    location: str
    skills: list[str]
    apply_url: str
    salary: str = ""
    experience: str = ""
    posted: str = ""
    source: str = "naukri"
    external_id: str = field(init=False)

    def __post_init__(self) -> None:
        key = f"naukri:{self.title}:{self.company}".lower()
        self.external_id = hashlib.md5(key.encode()).hexdigest()


class NaukriScraper:
    BASE = "https://www.naukri.com"

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._browser: Browser | None = None

    async def __aenter__(self) -> "NaukriScraper":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._browser:
            await self._browser.close()
        await self._playwright.stop()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _scrape_page(self, page: Page, url: str) -> list[ScrapedJob]:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)

        jobs: list[ScrapedJob] = []

        job_elements = await page.query_selector_all("article.jobTuple")
        if not job_elements:
            job_elements = await page.query_selector_all(".cust-job-tuple")

        for el in job_elements:
            try:
                title_el   = await el.query_selector(".title a, .jobTitle")
                company_el = await el.query_selector(".companyInfo a, .comp-name")
                loc_el     = await el.query_selector(".locWdth, .loc-nm")
                skill_els  = await el.query_selector_all(".tag, .skill-name")
                href_el    = await el.query_selector(".title a, .jobTitle a")

                title   = (await title_el.inner_text()).strip()   if title_el   else ""
                company = (await company_el.inner_text()).strip() if company_el else ""
                loc     = (await loc_el.inner_text()).strip()     if loc_el     else ""
                href    = await href_el.get_attribute("href")     if href_el    else ""

                skills = []
                for sk in skill_els:
                    text = (await sk.inner_text()).strip()
                    if text and len(text) < 50:
                        skills.append(text)

                if title and company:
                    jobs.append(
                        ScrapedJob(
                            title=title,
                            company=company,
                            location=loc,
                            skills=skills[:8],
                            apply_url=href or f"{self.BASE}/job",
                        )
                    )
            except Exception as e:
                log.warning("Failed to parse job element: %s", e)
                continue

        return jobs

    async def scrape(
        self,
        keywords: str,
        location: str = "india",
        pages: int = 3,
    ) -> list[ScrapedJob]:
        if not self._browser:
            raise RuntimeError("Call as async context manager")

        page = await self._browser.new_page()
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        all_jobs: list[ScrapedJob] = []
        keyword_slug = keywords.lower().replace(" ", "-")

        for p in range(1, pages + 1):
            url = f"{self.BASE}/{keyword_slug}-jobs-in-{location}-{p}"
            try:
                jobs = await self._scrape_page(page, url)
                all_jobs.extend(jobs)
                log.info("Naukri page %d/%d: %d jobs", p, pages, len(jobs))
                await asyncio.sleep(2)  # polite delay
            except Exception as e:
                log.error("Failed to scrape Naukri page %d: %s", p, e)
                break

        await page.close()
        # Deduplicate by external_id
        seen: set[str] = set()
        unique = []
        for job in all_jobs:
            if job.external_id not in seen:
                seen.add(job.external_id)
                unique.append(job)

        return unique


# ─── Run standalone ───────────────────────────────────────────────────────────

async def _demo() -> None:
    async with NaukriScraper(headless=True) as scraper:
        jobs = await scraper.scrape("python developer", "bangalore", pages=2)
        for j in jobs[:5]:
            print(f"  {j.title} @ {j.company} — {j.location}")
        print(f"Total: {len(jobs)} jobs scraped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_demo())
