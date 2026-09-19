from pathlib import Path

from playwright.async_api import Page, expect

from bills.core.downloads import Collector
from bills.core.secrets import Credentials
from bills.settings import settings

site = settings.site("water")

table = "water"


async def download_bill(
    page: Page, credentials: Credentials, collector: Collector
) -> list[Path]:
    await page.locator('[data-test="sign-in-email-input"]').fill(credentials.username)
    await page.locator('[data-test="sign-in-password-input"]').fill(
        credentials.password.get_secret_value()
    )
    await page.get_by_role("button", name="Sign In", exact=True).click()
    await page.get_by_role("button", name="VIEW/PAY BILL").click()
    await page.get_by_role("link", name="History").click()
    await page.wait_for_load_state("networkidle")

    export = page.get_by_role("button", name="Export")
    await expect(export).to_be_enabled()

    async with page.expect_download(timeout=30_000) as download_info:
        await export.click()
    return [await collector.save(await download_info.value)]
