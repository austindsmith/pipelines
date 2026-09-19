import argparse

from bills.core.warehouse import connect, count, load
from bills.settings import settings
from bills.sites import SITES


def main(names: list[str], *, rebuild: bool) -> None:
    with connect(settings.database) as connection:
        print(f"database: {settings.database}")
        for name in names:
            module = SITES[name]
            loaded = load(
                connection,
                module.table,
                module.site,
                settings.download_dir,
                rebuild=rebuild,
            )
            for origin, rows in loaded.items():
                print(f"{name}: +{rows} rows from {origin}")
            if not loaded:
                print(f"{name}: up to date")
            print(f"{name}: {count(connection, module.table)} rows total")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="bills.load",
        description="Load downloaded csvs into DuckDB.",
    )
    parser.add_argument(
        "sites",
        nargs="*",
        metavar="SITE",
        help=f"sites to load; defaults to all ({', '.join(SITES)})",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="drop every table and re-loads every csv instead of only new ones",
    )
    args = parser.parse_args()

    names = args.sites or list(SITES)
    if unknown := [name for name in names if name not in SITES]:
        parser.error(
            f"unknown site(s): {', '.join(unknown)} (choose from {', '.join(SITES)})"
        )
    main(names, rebuild=args.rebuild)
