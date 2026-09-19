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
