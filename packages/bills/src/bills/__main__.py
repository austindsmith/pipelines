import argparse
import asyncio

from bills.core.runner import run
from bills.core.secrets import op_client
from bills.sites import SITES


async def main(names: list[str]) -> None:
    client = await op_client()
    for name in names:
        module = SITES[name]
        paths = await run(module.site, module.download_bill, client)
        for path in paths:
            print(f"{name}: {path}")
        if not paths:
            print(f"{name}: nothing new")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="bills")
    parser.add_argument(
        "sites",
        nargs="*",
        metavar="SITE",
        help=f"sites to download; defaults to all ({', '.join(SITES)})",
    )
    args = parser.parse_args()

    names = args.sites or list(SITES)
    if unknown := [name for name in names if name not in SITES]:
        parser.error(
            f"unknown site(s): {', '.join(unknown)} (choose from {', '.join(SITES)})"
        )
    asyncio.run(main(names))
