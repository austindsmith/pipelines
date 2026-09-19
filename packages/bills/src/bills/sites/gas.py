import csv
import io
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from playwright.async_api import Locator, Page, expect

from bills.core.downloads import Collector
from bills.core.mailbox import security_code
from bills.core.secrets import Credentials, credentials_for
from bills.settings import settings

site = settings.site("gas")

table = "gas"

PDF = b"%PDF"
EOF = b"%%EOF"


async def download_bill(
    page: Page, credentials: Credentials, collector: Collector
) -> list[Path]:
    await sign_in(page, credentials)
    await verify(page)

    paths = [await payment_history(page, collector)]
    paths.extend(await bills(page, collector))
    return paths


async def sign_in(page: Page, credentials: Credentials) -> None:
    password = page.get_by_role("textbox", name="password")
    await page.get_by_role("textbox", name="email address username").fill(
        credentials.username
    )
    await password.fill(credentials.password.get_secret_value())
    await expect(password).not_to_be_empty()
    await page.get_by_role("button", name="Sign in").click()


async def verify(page: Page) -> None:
    requested = datetime.now(UTC)
    await page.get_by_role("button", name="Submit", exact=True).click()

    code = page.get_by_role("textbox", name="Code")
    await expect(code).to_be_visible()

    mailbox = await credentials_for(settings.site("gmail"))
    await code.fill(
        await security_code(
            mailbox,
            sender=settings.gas_code_sender,
            subject=settings.gas_code_subject,
            since=requested,
        )
    )
    await page.get_by_role("button", name="Submit", exact=True).click()
    await page.wait_for_load_state("networkidle")


async def navigate(page: Page, link: str) -> None:
    await page.get_by_role("button", name="mma home deskop").click()
    await page.get_by_role("link", name=link).click()
    await page.wait_for_load_state("networkidle")


async def payment_history(page: Page, collector: Collector) -> Path:
    await navigate(page, "payment history deskop")

    buffer = io.StringIO()
    csv.writer(buffer).writerows(await rows(await first_table(page)))
    return collector.write_text(buffer.getvalue(), ".csv")


async def bills(page: Page, collector: Collector) -> list[Path]:
    await navigate(page, "view bills list deskop")
    links = (await first_table(page)).locator("tbody a[href*='ViewBill']")

    pending: list[tuple[str, date]] = []
    for link in await links.all():
        href = await link.get_attribute("href")
        if href is None:
            continue
        href = urljoin(page.url, href)
        on = bill_date(href)
        if on is not None and not collector.has(".pdf", on):
            pending.append((href, on))

    return [await statement(page, href, collector, on) for href, on in pending]


async def statement(page: Page, href: str, collector: Collector, on: date) -> Path:
    response = await page.request.get(href)
    body = await response.body()
    if not response.ok:
        raise RuntimeError(f"{href} returned HTTP {response.status}")
    start = body.find(PDF)
    if start < 0:
        preview = body[:200].decode("utf-8", errors="replace")
        raise RuntimeError(f"{href} did not return a PDF, got: {preview!r}")
    end = body.rfind(EOF)
    if end < start:
        raise RuntimeError(f"{href} returned a truncated PDF")
    return collector.write_bytes(body[start : end + len(EOF)], ".pdf", on)


async def first_table(page: Page) -> Locator:
    locator = page.locator("table.table-striped").first
    await expect(locator).to_be_visible()
    return locator


async def rows(locator: Locator) -> list[list[str]]:
    headers = [
        text.strip() for text in await locator.locator("thead th").all_inner_texts()
    ]
    width = len([header for header in headers if header])

    table_rows = [headers[:width]]
    for row in await locator.locator("tbody tr").all():
        cells = [text.strip() for text in await row.locator("td").all_inner_texts()]
        table_rows.append(cells[:width])
    return table_rows


def bill_date(href: str) -> date | None:
    values = parse_qs(urlparse(href).query).get("BD")
    if not values:
        return None
    try:
        month, day, year = (int(part) for part in values[0].split("/"))
    except ValueError:
        return None
    return date(year, month, day)
