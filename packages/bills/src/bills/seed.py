import argparse
import asyncio

from bills.core.sheets import rows, session
from bills.core.warehouse import connect, replace
from bills.settings import settings


async def main(sheet_id: str, sheet_name: str, table: str) -> None:
    values = await asyncio.to_thread(rows, await session(), sheet_id, sheet_name)
    with connect(settings.database) as connection:
        loaded = replace(connection, table, values, sheet_name)
    print(f"database: {settings.database}")
    print(f"{table}: {loaded} rows from {sheet_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="bills.seed",
        description="Replace a DuckDB table with the contents of a Google Sheet tab.",
    )
    parser.add_argument("--sheet-id", default=settings.google_sheet_id)
    parser.add_argument("--sheet", default=settings.seed_sheet_name)
    parser.add_argument("--table", default=settings.seed_table)
    args = parser.parse_args()

    asyncio.run(main(args.sheet_id, args.sheet, args.table))
