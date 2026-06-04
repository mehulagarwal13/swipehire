"""
Internshala scraper — targets the internships/jobs listing pages.
Runs every 12 hours. Focused on 0-experience and student roles.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

log = logging.getLogger(__name__)


@dataclass
class InternshalaJob:
    title: str
    company: str
    location: str
    stipend: str
    duration: str
    skills: list[str]
    apply_url: str
    is_wfh: bool = False
    source: str = "internshala"
    external_id: str = field(init=False)

    def __post_init__(self) -> None:
        key = f"internshala:{self.title}:{self.company}".lower()
        self.external_id = hashlib.md5(key.encode()).hexdigest()


class IntershalaScraper:
    BASE = "https://internshala.com"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-IN,en;q=0.9",
    }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=8))
    async def _fetch(self, client: httpx.AsyncClient, url: str) -> str:
        resp = await client.get(url, timeout=20)
        resp.raise_for_status()
        return resp.text

    async def scrape_internships(self, category: str = "computer-science", pages: int = 3) -> list[InternshalaJob]:
        jobs: list[InternshalaJob] = []
        async with httpx.AsyncClient(headers=self.HEADERS, follow_redirects=True) as client:
            for p in range(1, pages + 1):
                url = f"{self.BASE}/internships/{category}-internship/page-{p}"
                try:
                    html = await self._fetch(client, url)
                    jobs.extend(self._parse_page(html))
                    await asyncio.sleep(1.5)
                except Exception as e:
                    log.error("Internshala page %d failed: %s", p, e)
        return self._deduplicate(jobs)

    def _parse_page(self, html: str) -> list[InternshalaJob]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(".individual_internship")
        jobs: list[InternshalaJob] = []

        for card in cards:
            try:
                title   = card.select_one(".profile")
                company = card.select_one(".company_name a, .company_name")
                loc_el  = card.select_one(".location_link, .locations_link")
                stipend = card.select_one(".stipend")
                dur     = card.select_one(".duration-mobile")
                skill_els = card.select(".round_tabs .round_tab")
                link_el = card.select_one("a.view_detail_button, .internship_meta a")

                if not title or not company:
                    continue

                is_wfh = bool(card.select_one(".work_from_home, .wfh_label"))
                href = link_el.get("href", "") if link_el else ""
                if href and not href.startswith("http"):
                    href = self.BASE + href

                jobs.append(InternshalaJob(
                    title=title.get_text(strip=True),
                    company=company.get_text(strip=True),
                    location=loc_el.get_text(strip=True) if loc_el else "India",
                    stipend=stipend.get_text(strip=True) if stipend else "",
                    duration=dur.get_text(strip=True) if dur else "",
                    skills=[s.get_text(strip=True) for s in skill_els[:6]],
                    apply_url=href,
                    is_wfh=is_wfh,
                ))
            except Exception as e:
                log.debug("Parse error: %s", e)
                continue

        return jobs

    def _deduplicate(self, jobs: list[InternshalaJob]) -> list[InternshalaJob]:
        seen: set[str] = set()
        result = []
        for j in jobs:
            if j.external_id not in seen:
                seen.add(j.external_id)
                result.append(j)
        return result


async def _demo() -> None:
    scraper = IntershalaScraper()
    jobs = await scraper.scrape_internships("computer-science", pages=2)
    for j in jobs[:5]:
        print(f"  {j.title} @ {j.company} — {j.location} — {j.stipend}")
    print(f"Total: {len(jobs)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_demo())
