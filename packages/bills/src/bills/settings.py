import subprocess
import tomllib
from datetime import date
from io import StringIO
from pathlib import Path

from dotenv import dotenv_values
from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def load_env(path: Path) -> dict[str, str]:
    text = path.read_text()
    if "sops_version" in text:
        text = subprocess.run(
            ["sops", "--decrypt", str(path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    return {
        key.lower(): value
        for key, value in dotenv_values(stream=StringIO(text)).items()
    }


def find_workspace_root(start: Path | None = None) -> Path:
    start = (start or Path(__file__)).resolve()
    if start.is_file():
        start = start.parent
    for directory in (start, *start.parents):
        pyproject = directory / "pyproject.toml"
        if not pyproject.exists():
            continue
        with pyproject.open("rb") as f:
            config = tomllib.load(f)
        if "workspace" in config.get("tool", {}).get("uv", {}):
            return directory
    raise RuntimeError("Could not find workspace root")


class Site(BaseModel):
    key: str
    item: str
    vault: str = "utilities"
    persistent: bool = False

    def ref(self, field: str) -> str:
        return f"op://{self.vault}/{self.item}/{field}"

    def download_path(self, base: Path, on: date | None = None) -> Path:
        on = on or date.today()
        return base / f"{on:%Y}" / f"{on:%m - %B}"

    def download_filename(self, suffix: str, on: date | None = None) -> str:
        on = on or date.today()
        return f"{self.item.lower().replace(' ', '_')}_{on:%Y_%m_%d}{suffix}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="ignore")

    op_service_account_token: SecretStr
    op_vault: str = "utilities"
    root_dir: Path = find_workspace_root()
    download_dir: Path
    duckdb_path: Path = find_workspace_root() / "data"
    duckdb_filename: str = "bills"
    headless: bool = False
    slow_mo: int = 0

    browser_channel: str | None = None
    browser_executable: Path | None = None
    imap_host: str = "imap.gmail.com"
    water: str
    electricity: str
    gas: str
    gas_code_sender: str
    gas_code_subject: str
    gmail: str = ""

    @property
    def database(self) -> Path:
        if self.duckdb_path.suffix == ".duckdb":
            return self.duckdb_path
        return self.duckdb_path / f"{self.duckdb_filename}.duckdb"

    def site(self, key: str, *, persistent: bool = False) -> Site:
        item = getattr(self, key, None)
        if not isinstance(item, str) or not item:
            raise ValueError(
                f"No 1Password item configured for {key!r}; "
                f"set {key.upper()} in secrets.env"
            )
        return Site(key=key, item=item, vault=self.op_vault, persistent=persistent)


ROOT_DIR = find_workspace_root()
settings = Settings(**load_env(ROOT_DIR / "secrets.env"))
