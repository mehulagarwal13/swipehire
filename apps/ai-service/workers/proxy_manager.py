"""
Rotating proxy manager for production scraping.

Supports:
  - Free proxy list rotation (dev/testing)
  - Oxylabs / Bright Data residential proxies (production)
  - 2Captcha integration for CAPTCHA bypass

Usage:
    async with ProxyManager() as pm:
        proxy = await pm.get_proxy()
        # use proxy in playwright: browser.new_context(proxy={"server": proxy})
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

from config import settings

log = logging.getLogger(__name__)


@dataclass
class Proxy:
    url: str              # e.g. "http://user:pass@host:port"
    failures: int = 0
    last_used: float = 0.0
    is_banned: bool = False

    def mark_failure(self) -> None:
        self.failures += 1
        if self.failures >= 3:
            self.is_banned = True
            log.warning("Proxy banned after 3 failures: %s", self.url)

    def mark_success(self) -> None:
        self.failures = 0
        self.last_used = time.time()


class ProxyManager:
    """
    Thread-safe rotating proxy pool.
    Falls back gracefully to direct (no-proxy) connection if pool empty.
    """

    def __init__(self) -> None:
        self._proxies: list[Proxy] = []
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "ProxyManager":
        await self._load_proxies()
        return self

    async def __aexit__(self, *_: object) -> None:
        pass

    async def _load_proxies(self) -> None:
        """Load proxies from config or fetch from provider."""
        proxies: list[Proxy] = []

        # 1. Oxylabs / Bright Data residential (production)
        if settings.proxy_username and settings.proxy_password:
            # Sticky session proxies for Oxylabs
            for port in range(10001, 10011):  # 10 sticky sessions
                proxies.append(Proxy(
                    url=f"http://{settings.proxy_username}:{settings.proxy_password}"
                        f"@{settings.proxy_host}:{port}"
                ))
            log.info("Loaded %d residential proxies", len(proxies))

        # 2. Static proxy list from config (comma-separated)
        if settings.proxy_list:
            for p in settings.proxy_list.split(","):
                p = p.strip()
                if p:
                    proxies.append(Proxy(url=p))

        # 3. Free proxies as last resort (dev only)
        if not proxies and settings.debug:
            proxies = await self._fetch_free_proxies()

        self._proxies = proxies

    async def _fetch_free_proxies(self) -> list[Proxy]:
        """Fetch free HTTPS proxies — unreliable, dev/test only."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.proxyscrape.com/v2/?request=getproxies"
                    "&protocol=http&timeout=5000&country=all&ssl=all&anonymity=elite"
                )
                lines = resp.text.strip().split("\r\n")
                proxies = [Proxy(url=f"http://{line.strip()}") for line in lines[:20] if line.strip()]
                log.info("Fetched %d free proxies", len(proxies))
                return proxies
        except Exception as e:
            log.warning("Failed to fetch free proxies: %s", e)
            return []

    async def get_proxy(self) -> Optional[dict]:
        """
        Returns a Playwright-compatible proxy dict, or None to use direct connection.
        {"server": "http://..."}
        """
        async with self._lock:
            available = [p for p in self._proxies if not p.is_banned]
            if not available:
                log.debug("No proxies available — using direct connection")
                return None

            # Prefer least recently used
            proxy = min(available, key=lambda p: p.last_used)
            return {"server": proxy.url}

    async def report_success(self, proxy_url: str) -> None:
        async with self._lock:
            for p in self._proxies:
                if p.url == proxy_url:
                    p.mark_success()
                    break

    async def report_failure(self, proxy_url: str) -> None:
        async with self._lock:
            for p in self._proxies:
                if p.url == proxy_url:
                    p.mark_failure()
                    break

    @property
    def pool_size(self) -> int:
        return len([p for p in self._proxies if not p.is_banned])


# ─── 2Captcha solver ──────────────────────────────────────────────────────────

class CaptchaSolver:
    """
    Solves reCAPTCHA v2/v3 via 2captcha.com API.
    Falls back gracefully (returns None) if API key not configured.
    """

    BASE = "https://2captcha.com"

    def __init__(self) -> None:
        self.api_key = settings.twocaptcha_api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def solve_recaptcha_v2(self, site_key: str, page_url: str) -> Optional[str]:
        """Returns the g-recaptcha-response token, or None on failure."""
        if not self.is_configured():
            log.debug("2captcha not configured — skipping CAPTCHA solve")
            return None

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                # Submit captcha
                resp = await client.post(f"{self.BASE}/in.php", data={
                    "key":       self.api_key,
                    "method":    "userrecaptcha",
                    "googlekey": site_key,
                    "pageurl":   page_url,
                    "json":      1,
                })
                data = resp.json()
                if data.get("status") != 1:
                    log.error("2captcha submit error: %s", data)
                    return None

                captcha_id = data["request"]
                log.info("2captcha: solving captcha %s", captcha_id)

                # Poll for result (up to 120 seconds)
                for _ in range(24):
                    await asyncio.sleep(5)
                    poll = await client.get(f"{self.BASE}/res.php", params={
                        "key":    self.api_key,
                        "action": "get",
                        "id":     captcha_id,
                        "json":   1,
                    })
                    result = poll.json()
                    if result.get("status") == 1:
                        log.info("2captcha: solved captcha %s", captcha_id)
                        return result["request"]
                    if result.get("request") != "CAPCHA_NOT_READY":
                        log.error("2captcha error: %s", result)
                        return None

                log.warning("2captcha: timed out waiting for captcha %s", captcha_id)
                return None

        except Exception as e:
            log.error("2captcha exception: %s", e)
            return None
