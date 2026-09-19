import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials

from bills.core.secrets import op_client
from bills.settings import settings

API = "https://sheets.googleapis.com/v4/spreadsheets"
READ_ONLY = "https://www.googleapis.com/auth/spreadsheets.readonly"
READ_WRITE = "https://www.googleapis.com/auth/spreadsheets"


async def service_account() -> dict[str, Any]:
    reference = settings.google_credentials
    if not reference:
        raise ValueError(
            "No Google service account configured; set BILLS_GOOGLE_CREDENTIALS "
            "in secrets.env to an op:// reference or a path to the key json"
        )
    if reference.startswith("op://"):
        client = await op_client()
        return json.loads(await client.secrets.resolve(reference))
    path = Path(reference).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"No Google service account key at {path}")
    return json.loads(path.read_text())


async def session(*, writable: bool = False) -> AuthorizedSession:
    info = await service_account()
    scopes = [READ_WRITE] if writable else [READ_ONLY]
    return AuthorizedSession(Credentials.from_service_account_info(info, scopes=scopes))


def rows(
    authorized: AuthorizedSession, sheet_id: str, sheet_name: str
) -> list[list[str]]:
    if not sheet_id:
        raise ValueError("No sheet id configured; set BILLS_GOOGLE_SHEET_ID")
    response = authorized.get(
        f"{API}/{sheet_id}/values/{quote(sheet_name, safe='')}",
        params={"majorDimension": "ROWS", "valueRenderOption": "FORMATTED_VALUE"},
    )
    if response.status_code in (403, 404):
        raise RuntimeError(
            f"Sheet {sheet_id!r} tab {sheet_name!r} returned HTTP "
            f"{response.status_code}; share the spreadsheet with the service "
            f"account email and confirm the tab name"
        )
    if not response.ok:
        raise RuntimeError(
            f"Sheets API returned HTTP {response.status_code}: {response.text[:200]}"
        )
    return [
        [cell if isinstance(cell, str) else str(cell) for cell in row]
        for row in response.json().get("values", [])
    ]
