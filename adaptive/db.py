from __future__ import annotations

from pathlib import Path
from typing import Optional


def get_engine(conn_str: str):
    try:
        from sqlalchemy import create_engine
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("Missing dependency: sqlalchemy") from exc

    return create_engine(conn_str)


def exec_sql_file(conn_str: str, sql_path: str | Path) -> None:
    """Execute a .sql file against the configured database."""

    from sqlalchemy import text

    engine = get_engine(conn_str)
    sql_path = Path(sql_path)
    sql = sql_path.read_text(encoding="utf-8")

    # Extremely simple splitter. v1 assumes the SQL file is safe to run as-is.
    # If we need transactional/migration semantics, we can switch to Alembic.
    statements = [s.strip() for s in sql.split(";") if s.strip()]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
