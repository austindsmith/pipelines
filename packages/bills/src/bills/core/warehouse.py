import re
from pathlib import Path

import duckdb

from bills.settings import Site

SOURCE = "_source"
LOADED_AT = "_loaded_at"
READER = "read_csv(?, all_varchar=true, normalize_names=true)"
NOW = "now() AT TIME ZONE 'UTC'"


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def identifier(name: str) -> str:
    return '"{}"'.format(name.replace('"', '""'))


def connect(database: Path) -> duckdb.DuckDBPyConnection:
    database.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(database)


def exports(site: Site, base: Path) -> list[Path]:
    prefix = f"{slug(site.item)}_"
    return sorted(
        path
        for path in base.rglob("*")
        if path.is_file()
        and path.suffix.lower() == ".csv"
        and slug(path.stem).startswith(prefix)
    )


def source(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


def has_table(connection: duckdb.DuckDBPyConnection, name: str) -> bool:
    found = connection.execute(
        "SELECT count(*) FROM duckdb_tables() WHERE table_name = ?", [name]
    ).fetchone()
    return bool(found and found[0])


def loaded(connection: duckdb.DuckDBPyConnection, name: str) -> set[str]:
    if not has_table(connection, name):
        return set()
    rows = connection.execute(
        f"SELECT DISTINCT {identifier(SOURCE)} FROM {identifier(name)}"
    ).fetchall()
    return {row[0] for row in rows}


def insert(
    connection: duckdb.DuckDBPyConnection, name: str, path: Path, origin: str
) -> int:
    table = identifier(name)
    select = (
        f"SELECT *, ? AS {identifier(SOURCE)}, {NOW} AS {identifier(LOADED_AT)} "
        f"FROM {READER}"
    )
    statement = (
        f"INSERT INTO {table} BY NAME {select}"
        if has_table(connection, name)
        else f"CREATE TABLE {table} AS {select}"
    )
    try:
        connection.execute(statement, [origin, str(path)])
    except duckdb.Error as error:
        raise RuntimeError(f"could not load {origin}: {error}") from error
    return connection.execute(
        f"SELECT count(*) FROM {table} WHERE {identifier(SOURCE)} = ?", [origin]
    ).fetchone()[0]


def columns(header: list[str]) -> list[str]:
    names: list[str] = []
    for index, value in enumerate(header):
        name = slug(value) or f"column_{index + 1}"
        while name in names:
            name = f"{name}_{index + 1}"
        names.append(name)
    return names


def fit(row: list[str], width: int) -> list[str | None]:
    padded: list[str | None] = list(row[:width])
    return padded + [None] * (width - len(padded))


def replace(
    connection: duckdb.DuckDBPyConnection,
    name: str,
    values: list[list[str]],
    origin: str,
) -> int:
    if not values:
        raise RuntimeError(f"{origin} has no header row")

    table = identifier(name)
    header, *body = values
    names = columns(header)
    declared = ", ".join(f"{identifier(column)} VARCHAR" for column in names)
    connection.execute(
        f"CREATE OR REPLACE TABLE {table} ({declared}, "
        f"{identifier(SOURCE)} VARCHAR, {identifier(LOADED_AT)} TIMESTAMP)"
    )
    if body:
        placeholders = ", ".join(["?"] * len(names))
        connection.executemany(
            f"INSERT INTO {table} VALUES ({placeholders}, ?, {NOW})",
            [[*fit(row, len(names)), origin] for row in body],
        )
    return count(connection, name)


def load(
    connection: duckdb.DuckDBPyConnection,
    name: str,
    site: Site,
    base: Path,
    *,
    rebuild: bool = False,
) -> dict[str, int]:
    if rebuild:
        connection.execute(f"DROP TABLE IF EXISTS {identifier(name)}")

    already = loaded(connection, name)
    pending = [
        (path, source(path, base))
        for path in exports(site, base)
        if source(path, base) not in already
    ]
    return {origin: insert(connection, name, path, origin) for path, origin in pending}


def count(connection: duckdb.DuckDBPyConnection, name: str) -> int:
    if not has_table(connection, name):
        return 0
    return connection.execute(f"SELECT count(*) FROM {identifier(name)}").fetchone()[0]
