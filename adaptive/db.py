from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, unquote, urlparse


class _PsycoResult:
    def __init__(self, cursor: Any):
        self._cursor = cursor

    def scalar_one(self):
        row = self._cursor.fetchone()
        if not row:
            raise RuntimeError("No rows returned.")
        return row[0]


class _PsycoConnProxy:
    def __init__(self, cursor: Any):
        self._cursor = cursor

    def exec_driver_sql(self, sql: str, params: Any = None):
        self._cursor.execute(sql, params)
        return _PsycoResult(self._cursor)


class _PsycoEngine:
    def __init__(self, conn_str: str):
        self._conn_str = conn_str

    @contextmanager
    def begin(self):
        conn = _psycopg2_connect(self._conn_str)
        cur = conn.cursor()
        try:
            yield _PsycoConnProxy(cur)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                cur.close()
            finally:
                conn.close()


def _psycopg2_connect(conn_str: str):
    try:
        import psycopg2  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Missing dependency: neither sqlalchemy nor psycopg2 is available."
        ) from exc

    kwargs = _conn_kwargs_from_conn_str(conn_str)
    try:
        if kwargs is None:
            return psycopg2.connect(conn_str)
        return psycopg2.connect(**kwargs)
    except Exception as exc:
        if kwargs is None:
            info = "dsn=<raw>"
        else:
            info = (
                f"host={kwargs.get('host')} port={kwargs.get('port')} "
                f"dbname={kwargs.get('dbname')} user={kwargs.get('user')}"
            )
        raise RuntimeError(f"psycopg2 connection failed ({info}): {exc!r}") from exc


def _conn_kwargs_from_conn_str(conn_str: str) -> dict[str, Any] | None:
    if "://" not in conn_str:
        return None

    parsed = urlparse(conn_str)
    scheme = (parsed.scheme or "").lower()
    if not scheme.startswith("postgresql"):
        return None

    kwargs: dict[str, Any] = {}
    if parsed.hostname:
        kwargs["host"] = parsed.hostname
    if parsed.port:
        kwargs["port"] = int(parsed.port)
    if parsed.username:
        kwargs["user"] = unquote(parsed.username)
    if parsed.password:
        kwargs["password"] = unquote(parsed.password)
    db_name = (parsed.path or "").lstrip("/")
    if db_name:
        kwargs["dbname"] = unquote(db_name)

    for k, v in parse_qsl(parsed.query or "", keep_blank_values=False):
        if k and k not in kwargs:
            kwargs[k] = v

    return kwargs


def get_engine(conn_str: str):
    try:
        from sqlalchemy import create_engine
        return create_engine(conn_str)
    except Exception:
        # Fallback sem SQLAlchemy (ambiente mínimo no servidor/QGIS).
        return _PsycoEngine(conn_str)


def exec_sql_file(conn_str: str, sql_path: str | Path) -> None:
    """Execute a .sql file against the configured database."""

    engine = get_engine(conn_str)
    sql_path = Path(sql_path)
    sql = sql_path.read_text(encoding="utf-8")

    with engine.begin() as conn:
        # Preferred path: let PostgreSQL parse the full script.
        # This avoids broken splits when ';' appears inside comments.
        try:
            conn.exec_driver_sql(sql)
            return
        except Exception as first_exc:
            # Fallback: split conservatively for environments/drivers that do
            # not accept multi-statement execution in a single call.
            statements = _split_sql_statements_no_comments(sql)
            if not statements:
                raise first_exc
            for stmt in statements:
                conn.exec_driver_sql(stmt)


def _split_sql_statements_no_comments(sql: str) -> list[str]:
    lines = []
    for raw_line in sql.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("--"):
            continue
        lines.append(raw_line)

    compact_sql = "\n".join(lines)
    statements = [s.strip() for s in compact_sql.split(";") if s.strip()]
    return statements
