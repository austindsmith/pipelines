from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import stamina
from onepassword.client import Client
from playwright.async_api import (
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from bills.core.downloads import Collector
from bills.core.secrets import Credentials, SiteLogin, login_for
from bills.settings import Site, settings

Scraper = Callable[[Page, Credentials, Collector], Awaitable[Sequence[Path]]]


async def run(site: Site, scraper: Scraper, client: Client | None = None) -> list[Path]:
    login = await login_for(site, client)
    return await attempt(site, login, scraper)


@stamina.retry(on=PlaywrightTimeoutError, attempts=3, timeout=None)
async def attempt(site: Site, login: SiteLogin, scraper: Scraper) -> list[Path]:
    async with async_playwright() as p:
        context = await open_context(p, site)
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.pages[0] if context.pages else await context.new_page()
        collector = Collector(site, settings.download_dir)
        try:
            await page.goto(login.url)
            paths = list(await scraper(page, login.credentials, collector))
            await context.tracing.stop()
            return paths
        except Exception:
            await save_failure(page, context, site)
            raise
        finally:
            await context.close()


def launch_options() -> dict[str, Any]:
    options: dict[str, Any] = {
        "headless": settings.headless,
        "slow_mo": settings.slow_mo,
    }
    if settings.browser_channel:
        options["channel"] = settings.browser_channel
    elif settings.browser_executable:
        options["executable_path"] = str(settings.browser_executable)
    return options


async def open_context(p: Playwright, site: Site) -> BrowserContext:
    if site.persistent:
        return await p.chromium.launch_persistent_context(
            settings.root_dir / ".browser" / site.key,
            accept_downloads=True,
            args=["--disable-blink-features=AutomationControlled"],
            **launch_options(),
        )
    browser = await p.chromium.launch(**launch_options())
    return await browser.new_context(accept_downloads=True)


async def save_failure(page: Page, context: BrowserContext, site: Site) -> None:
    directory = settings.download_dir / "failures"
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"{site.key}_{datetime.now():%Y_%m_%d_%H%M%S}"
    await page.screenshot(path=directory / f"{stem}.png")
    await context.tracing.stop(path=directory / f"{stem}.zip")
