import subprocess
import tomllib
from io import StringIO
from pathlib import Path

from dotenv import dotenv_values


def load_sops_env(path: str) -> dict[str, str]:
    result = subprocess.run(
        ["sops", "--decrypt", path],
        check=True,
        capture_output=True,
        text=True,
    )
    return dict(dotenv_values(stream=StringIO(result.stdout)))


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


WORKSPACE_ROOT = find_workspace_root()
token_file = WORKSPACE_ROOT / "1password.env"
secrets = load_sops_env(str(token_file))
OP_SERVICE_ACCOUNT_TOKEN = secrets["OP_SERVICE_ACCOUNT_TOKEN"]
