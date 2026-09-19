import asyncio
from typing import NamedTuple

from onepassword.client import Client
from pydantic import SecretStr

from bills.settings import Site, settings


class Credentials(NamedTuple):
    username: str
    password: SecretStr


class SiteLogin(NamedTuple):
    url: str
    credentials: Credentials


async def op_client() -> Client:
    return await Client.authenticate(
        auth=settings.op_service_account_token.get_secret_value(),
        integration_name="bills",
        integration_version="0.1.0",
    )


async def credentials_for(site: Site, client: Client | None = None) -> Credentials:
    client = client or await op_client()
    username, password = await asyncio.gather(
        client.secrets.resolve(site.ref("username")),
        client.secrets.resolve(site.ref("password")),
    )
    return Credentials(username, SecretStr(password))


async def website_for(site: Site, client: Client | None = None) -> str:
    client = client or await op_client()
    vaults = await client.vaults.list()
    vault = next((v for v in vaults if v.title == site.vault), None)
    if vault is None:
        raise LookupError(f"No 1Password vault titled {site.vault!r}")

    overviews = await client.items.list(vault.id)
    overview = next((o for o in overviews if o.title == site.item), None)
    if overview is None:
        raise LookupError(f"No 1Password item for {site.key!r} in {site.vault!r}")

    item = await client.items.get(vault.id, overview.id)
    website = next(iter(item.websites), None)
    if website is None:
        raise LookupError(f"1Password item for {site.key!r} has no website")
    return website.url


async def login_for(site: Site, client: Client | None = None) -> SiteLogin:
    client = client or await op_client()
    url, credentials = await asyncio.gather(
        website_for(site, client),
        credentials_for(site, client),
    )
    return SiteLogin(url, credentials)
