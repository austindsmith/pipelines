import asyncio
import email
import imaplib
import re
import time
from datetime import UTC, datetime, timedelta
from email.message import Message
from email.utils import parsedate_to_datetime

from bills.core.secrets import Credentials
from bills.settings import settings

SECURITY_CODE = re.compile(r"security code is\s*(\d{4,8})", re.IGNORECASE)

SKEW = timedelta(minutes=2)


async def security_code(
    credentials: Credentials,
    *,
    sender: str,
    subject: str,
    since: datetime,
    pattern: re.Pattern[str] = SECURITY_CODE,
    timeout: float = 180,
    interval: float = 5,
) -> str:
    deadline = time.monotonic() + timeout
    while True:
        code = await asyncio.to_thread(
            search, credentials, sender, subject, since - SKEW, pattern
        )
        if code is not None:
            return code
        if time.monotonic() >= deadline:
            raise TimeoutError(
                f"No message from {sender} matching {subject!r} arrived "
                f"within {timeout:.0f}s of {since:%Y-%m-%d %H:%M:%S %Z}"
            )
        await asyncio.sleep(interval)


def search(
    credentials: Credentials,
    sender: str,
    subject: str,
    since: datetime,
    pattern: re.Pattern[str],
) -> str | None:
    with imaplib.IMAP4_SSL(settings.imap_host) as imap:
        imap.login(credentials.username, credentials.password.get_secret_value())
        imap.select("INBOX", readonly=True)
        status, data = imap.search(
            None,
            "FROM",
            quote(sender),
            "SUBJECT",
            quote(subject),
            "SINCE",
            f"{since:%d-%b-%Y}",
        )
        if status != "OK":
            raise RuntimeError(f"IMAP search failed: {status}")

        for identifier in reversed(data[0].split()):
            status, fetched = imap.fetch(identifier, "(RFC822)")
            if status != "OK":
                continue
            message = parse(fetched)
            if message is None or received_at(message) < since:
                continue
            if match := pattern.search(body(message)):
                return match.group(1)
    return None


def quote(value: str) -> str:
    return '"{}"'.format(value.replace("\\", r"\\").replace('"', r"\""))


def parse(fetched: list) -> Message | None:
    for part in fetched:
        if isinstance(part, tuple) and isinstance(part[1], bytes):
            return email.message_from_bytes(part[1])
    return None


def received_at(message: Message) -> datetime:
    raw = message.get("Date")
    if raw is None:
        return datetime.min.replace(tzinfo=UTC)
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=UTC)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def body(message: Message) -> str:
    parts = message.walk() if message.is_multipart() else [message]
    chunks = []
    for part in parts:
        if part.get_content_maintype() != "text":
            continue
        payload = part.get_payload(decode=True)
        if isinstance(payload, bytes):
            charset = part.get_content_charset() or "utf-8"
            chunks.append(payload.decode(charset, errors="replace"))
    return "\n".join(chunks)
