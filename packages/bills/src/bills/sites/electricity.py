from pathlib import Path

from playwright.async_api import Page, expect

from bills.core.downloads import Collector
from bills.core.secrets import Credentials
from bills.settings import settings

site = settings.site("electricity", persistent=True)

table = "electricity"


async def download_bill(
    page: Page, credentials: Credentials, collector: Collector
) -> list[Path]:
    await page.get_by_role("link", name="Log In to My Account").click()

    password = page.get_by_role("textbox", name="Password")
    await page.get_by_role("textbox", name="Email address").fill(credentials.username)
    await password.click()
    await password.fill(credentials.password.get_secret_value())
    await expect(password).not_to_be_empty()
    await page.get_by_role("button", name="Log In").click()

    await page.get_by_role("link", name="Payment History").click()
    await page.wait_for_load_state("networkidle")

    csv_option = page.locator("#downloadOption2")
    await csv_option.click()
    await expect(csv_option).to_be_checked()

    download_button = page.get_by_role("button", name="Download", exact=True)
    await expect(download_button).to_be_visible()
    await expect(download_button).to_be_enabled()

    async with page.expect_download(timeout=30_000) as download_info:
        await download_button.click()
    return [await collector.save(await download_info.value)]
