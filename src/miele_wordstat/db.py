from __future__ import annotations

from pathlib import Path

import duckdb

from .config import Settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = PROJECT_ROOT / "sql"


def schema_files() -> list[Path]:
    return [
        SQL_DIR / "create_tables.sql",
        SQL_DIR / "views.sql",
    ]


def initialize_database(settings: Settings) -> None:
    settings.duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(settings.duckdb_path)) as con:
        for sql_file in schema_files():
            con.execute(sql_file.read_text())


def database_summary(settings: Settings) -> dict[str, int | bool]:
    if not settings.duckdb_path.exists():
        return {"exists": False}

    with duckdb.connect(str(settings.duckdb_path), read_only=True) as con:
        table_rows = con.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema = 'main'
              and table_type = 'BASE TABLE'
            """
        ).fetchall()
        view_rows = con.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema = 'main'
              and table_type = 'VIEW'
            """
        ).fetchall()

    return {
        "exists": True,
        "tables": len(table_rows),
        "views": len(view_rows),
    }
