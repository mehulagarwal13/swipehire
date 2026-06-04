"""
Auto-Apply Engine — fills and submits job applications via Playwright.

Supported portals (Phase 1):
  - Naukri.com
  - Lever-based portals  (jobs.lever.co)
  - Greenhouse-based     (boards.greenhouse.io)
  - Internshala

Flow:
  POST /swipes (direction=right)
    → auto_apply_service.queue(user_id, job_id)
      → worker picks up job from Redis queue
        → AutoApplyWorker.run()
          → detect_portal_type()
          → fill appropriate form
          → upload resume
          → submit
          → capture screenshot + confirmation URL
          → update application status
"""
from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import httpx
from playwright.async_api import Page, async_playwright

log = logging.getLogger(__name__)


class PortalType(str, Enum):
    NAUKRI      = "naukri"
    LEVER       = "lever"
    GREENHOUSE  = "greenhouse"
    INTERNSHALA = "internshala"
    UNKNOWN     = "unknown"


@dataclass
class ApplyResult:
    success: bool
    portal: PortalType
    confirmation_url: str = ""
    screenshot_bytes: bytes = b""
    error: str = ""


@dataclass
class UserApplyData:
    """Flattened profile fields needed to fill any application form."""
    full_name: str
    email: str
    phone: str
    resume_url: str          # R2 URL — will be downloaded to temp file
    headline: str = ""
    current_location: str = ""
    experience_years: float = 0.0
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    notice_period_days: int = 30
    current_salary_lpa: float = 0.0
    expected_salary_lpa: float = 0.0
    cover_letter: str = ""


# ─── Portal detection ─────────────────────────────────────────────────────────

async def detect_portal_type(page: Page, url: str) -> PortalType:
    if "naukri.com" in url:
        return PortalType.NAUKRI
    if "lever.co" in url:
        return PortalType.LEVER
    if "greenhouse.io" in url or "boards.greenhouse" in url:
        return PortalType.GREENHOUSE
    if "internshala.com" in url:
        return PortalType.INTERNSHALA

    # Try to detect from page content
    content = await page.content()
    if "lever-job-board" in content or "lever-apply" in content:
        return PortalType.LEVER
    if "greenhouse-job-board" in content:
        return PortalType.GREENHOUSE

    return PortalType.UNKNOWN


# ─── Portal-specific form fillers ─────────────────────────────────────────────

async def _fill_text_if_exists(page: Page, selector: str, value: str) -> bool:
    """Fill a field if it exists on the page. Returns True if found."""
    try:
        el = page.locator(selector).first
        if await el.count() > 0:
            await el.fill(value)
            return True
    except Exception:
        pass
    return False


async def fill_lever_form(page: Page, data: UserApplyData, resume_path: str) -> None:
    """Lever apply page: /apply endpoint with standard fields."""
    await _fill_text_if_exists(page, "input[name='name']",                    data.full_name)
    await _fill_text_if_exists(page, "input[name='email']",                   data.email)
    await _fill_text_if_exists(page, "input[name='phone']",                   data.phone)
    await _fill_text_if_exists(page, "input[name='org']",                     "")
    await _fill_text_if_exists(page, "input[name='urls[LinkedIn]']",          data.linkedin_url)
    await _fill_text_if_exists(page, "input[name='urls[GitHub]']",            data.github_url)
    await _fill_text_if_exists(page, "input[name='urls[Portfolio]']",         data.portfolio_url)
    await _fill_text_if_exists(page, "textarea[name='comments']",             data.cover_letter)

    # Resume file upload
    file_input = page.locator("input[type='file']").first
    if await file_input.count() > 0:
        await file_input.set_input_files(resume_path)

    await page.wait_for_timeout(1000)


async def fill_greenhouse_form(page: Page, data: UserApplyData, resume_path: str) -> None:
    """Greenhouse job board apply form."""
    await _fill_text_if_exists(page, "#first_name",         data.full_name.split()[0])
    await _fill_text_if_exists(page, "#last_name",          " ".join(data.full_name.split()[1:]) or data.full_name)
    await _fill_text_if_exists(page, "#email",              data.email)
    await _fill_text_if_exists(page, "#phone",              data.phone)
    await _fill_text_if_exists(page, "#job_application_answers_attributes_0_answer", data.cover_letter)

    file_input = page.locator("input[type='file']#resume").first
    if await file_input.count() > 0:
        await file_input.set_input_files(resume_path)

    await page.wait_for_timeout(1000)


async def fill_naukri_form(page: Page, data: UserApplyData) -> None:
    """
    Naukri one-click apply — works when user is logged in to Naukri.
    In production: store Naukri session cookies per user.
    Here we fill the quick-apply modal if it appears.
    """
    # Look for the quick apply button and click it
    apply_btn = page.locator("button:has-text('Apply'), a:has-text('Apply Now')").first
    if await apply_btn.count() > 0:
        await apply_btn.click()
        await page.wait_for_timeout(1500)

    # Fill modal fields if present
    await _fill_text_if_exists(page, "input[placeholder*='name' i]",    data.full_name)
    await _fill_text_if_exists(page, "input[placeholder*='email' i]",   data.email)
    await _fill_text_if_exists(page, "input[placeholder*='phone' i]",   data.phone)
    await _fill_text_if_exists(page, "input[placeholder*='notice' i]",  str(data.notice_period_days))
    await _fill_text_if_exists(page, "input[placeholder*='current salary' i]", str(data.current_salary_lpa))
    await _fill_text_if_exists(page, "input[placeholder*='expected' i]",       str(data.expected_salary_lpa))


async def fill_internshala_form(page: Page, data: UserApplyData, resume_path: str) -> None:
    """Internshala application form — requires login session."""
    await _fill_text_if_exists(page, "textarea[name='cover_letter'], #cover_letter", data.cover_letter or
        f"Dear Hiring Team, I am {data.full_name}, a {data.headline} with {data.experience_years:.0f} years of experience. "
        f"I am excited to apply for this role and believe my skills are a strong match. "
        f"Please find my resume attached. Looking forward to hearing from you.")

    file_input = page.locator("input[type='file']").first
    if await file_input.count() > 0:
        await file_input.set_input_files(resume_path)


# ─── Resume download helper ───────────────────────────────────────────────────

async def download_resume_to_temp(resume_url: str) -> str:
    """Download resume from R2 to a temp file. Returns the temp file path."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(resume_url, timeout=30)
        resp.raise_for_status()

    suffix = ".pdf" if "pdf" in resume_url.lower() else ".docx"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(resp.content)
    tmp.close()
    return tmp.name


# ─── Main worker ─────────────────────────────────────────────────────────────

class AutoApplyWorker:
    """
    Stateless worker — each apply job creates a fresh browser context.
    Call from Celery task or directly.
    """

    async def run(self, apply_url: str, user_data: UserApplyData) -> ApplyResult:
        resume_path: str | None = None

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                viewport={"width": 1280, "height": 900},
            )
            page = await context.new_page()

            try:
                await page.goto(apply_url, wait_until="networkidle", timeout=30000)
                portal = await detect_portal_type(page, apply_url)
                log.info("Auto-apply: %s portal detected for %s", portal, apply_url)

                # Download resume once
                if user_data.resume_url:
                    resume_path = await download_resume_to_temp(user_data.resume_url)

                # Fill form based on portal type
                if portal == PortalType.LEVER:
                    await fill_lever_form(page, user_data, resume_path or "")
                elif portal == PortalType.GREENHOUSE:
                    await fill_greenhouse_form(page, user_data, resume_path or "")
                elif portal == PortalType.NAUKRI:
                    await fill_naukri_form(page, user_data)
                elif portal == PortalType.INTERNSHALA:
                    await fill_internshala_form(page, user_data, resume_path or "")
                else:
                    log.warning("Unknown portal — attempting generic fill")
                    await self._generic_fill(page, user_data, resume_path or "")

                # Submit
                submit_btn = page.locator(
                    "button[type='submit'], input[type='submit'], button:has-text('Submit'), button:has-text('Apply')"
                ).first
                if await submit_btn.count() > 0:
                    await submit_btn.click()
                    await page.wait_for_load_state("networkidle", timeout=15000)

                screenshot = await page.screenshot(type="png")
                confirmation_url = page.url

                return ApplyResult(
                    success=True,
                    portal=portal,
                    confirmation_url=confirmation_url,
                    screenshot_bytes=screenshot,
                )

            except Exception as e:
                log.exception("Auto-apply failed for %s", apply_url)
                screenshot = await page.screenshot(type="png") if page else b""
                return ApplyResult(
                    success=False,
                    portal=PortalType.UNKNOWN,
                    screenshot_bytes=screenshot,
                    error=str(e),
                )
            finally:
                if resume_path:
                    Path(resume_path).unlink(missing_ok=True)
                await browser.close()

    async def _generic_fill(self, page: Page, data: UserApplyData, resume_path: str) -> None:
        """Best-effort fill for unknown portals using common field patterns."""
        common_name_selectors = [
            "input[name='name']", "input[id*='name' i]", "input[placeholder*='name' i]",
            "input[name='full_name']", "input[name='fullname']",
        ]
        for sel in common_name_selectors:
            if await _fill_text_if_exists(page, sel, data.full_name):
                break

        await _fill_text_if_exists(page, "input[type='email']", data.email)
        await _fill_text_if_exists(page, "input[type='tel']",   data.phone)

        if resume_path:
            file_input = page.locator("input[type='file']").first
            if await file_input.count() > 0:
                await file_input.set_input_files(resume_path)

        await page.wait_for_timeout(500)
