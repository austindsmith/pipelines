from dataclasses import dataclass
from datetime import date
from pathlib import Path

from playwright.async_api import Download

from bills.settings import Site


@dataclass(frozen=True)
class Collector:
    site: Site
    base: Path

    def path(self, suffix: str, on: date | None = None) -> Path:
        directory = self.site.download_path(self.base, on)
        return directory / self.site.download_filename(suffix, on)

    def has(self, suffix: str, on: date | None = None) -> bool:
        return self.path(suffix, on).exists()

    async def save(self, download: Download, on: date | None = None) -> Path:
        suffix = Path(download.suggested_filename).suffix
        path = self.prepare(suffix, on)
        await download.save_as(path)
        return path

    def write_bytes(self, content: bytes, suffix: str, on: date | None = None) -> Path:
        path = self.prepare(suffix, on)
        path.write_bytes(content)
        return path

    def write_text(self, content: str, suffix: str, on: date | None = None) -> Path:
        path = self.prepare(suffix, on)
        path.write_text(content)
        return path

    def prepare(self, suffix: str, on: date | None = None) -> Path:
        path = self.path(suffix, on)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
