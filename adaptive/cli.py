from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from adaptive.db import exec_sql_file, get_engine
from adaptive.settings import Settings


def _cmd_init_db(args: argparse.Namespace) -> int:
    s = Settings.from_env()
    try:
        s.validate()
    except Exception as exc:
        print(f"[fail] settings: {exc!r}")
        return 2

    sql_path = Path(args.sql_file)
    if not sql_path.exists():
        raise SystemExit(f"SQL file not found: {sql_path}")

    try:
        exec_sql_file(s.pg_conn_str, sql_path)
        print(f"[ok] schema applied: {sql_path}")
        return 0
    except Exception as exc:
        print(f"[fail] init-db: {exc!r}")
        return 2


def _cmd_doctor(args: argparse.Namespace) -> int:
    s = Settings.from_env()
    try:
        s.validate()
    except Exception as exc:
        print(f"[fail] settings: {exc!r}")
        return 2

    try:
        engine = get_engine(s.pg_conn_str)
        with engine.begin() as conn:
            conn.exec_driver_sql("SELECT 1")
        print("[ok] db connection")
    except Exception as exc:
        print(f"[fail] db connection: {exc!r}")
        return 2

    print(f"[ok] orbital_dir: {s.orbital_dir}")
    print(f"[ok] artifacts_dir: {s.artifacts_dir}")

    if args.check_tables:
        # Optional checks; warn instead of failing.
        checks = [
            ("carto.folhas_cartograficas", "folha geometry"),
            ("litologia.litologia_100k", "lithology polygons"),
        ]
        engine = get_engine(s.pg_conn_str)
        with engine.begin() as conn:
            for table, label in checks:
                try:
                    conn.exec_driver_sql(f"SELECT 1 FROM {table} LIMIT 1")
                    print(f"[ok] table {table} ({label})")
                except Exception as exc:
                    print(f"[warn] table {table} missing/unreadable: {exc!r}")

    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    """MVP stub: create a run record and exit.

    The full run orchestration will be implemented in `adaptive/pipeline/run.py`.
    """

    s = Settings.from_env()
    try:
        s.validate()
    except Exception as exc:
        print(f"[fail] settings: {exc!r}")
        return 2

    engine = get_engine(s.pg_conn_str)

    now = datetime.utcnow().isoformat() + "Z"
    config_json = {
        "folha": args.folha,
        "data_ref": args.data_ref,
        "model": args.model,
        "created_at": now,
    }

    insert_sql = """
        INSERT INTO ml.run (folha_codigo, data_ref, status, config_json, model_backend, started_at, error_message)
        VALUES (%(folha)s, %(data_ref)s, %(status)s, %(config_json)s::jsonb, %(model_backend)s, now(), %(error_message)s)
        RETURNING id;
    """

    try:
        with engine.begin() as conn:
            rid = conn.exec_driver_sql(
                insert_sql,
                {
                    "folha": args.folha,
                    "data_ref": args.data_ref,
                    "status": "failed",
                    "config_json": json.dumps(config_json),
                    "model_backend": args.model,
                    "error_message": "run pipeline not implemented yet (scaffold)",
                },
            ).scalar_one()
        print(str(rid))
        return 1
    except Exception as exc:
        print(f"[fail] could not create run: {exc!r}")
        return 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="adaptive", description="Preditor Terra adaptive loop CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init-db", help="Apply the adaptive loop schema to PostGIS")
    p_init.add_argument(
        "--sql-file",
        default=str(Path("sql") / "adaptive_schema.sql"),
        help="Path to SQL schema file (default: sql/adaptive_schema.sql)",
    )
    p_init.set_defaults(func=_cmd_init_db)

    p_doc = sub.add_parser("doctor", help="Check DB connectivity and basic prerequisites")
    p_doc.add_argument("--check-tables", action="store_true", help="Also check for expected source tables")
    p_doc.set_defaults(func=_cmd_doctor)

    p_run = sub.add_parser("run", help="Run a folha update job (stub in v0.1)")
    p_run.add_argument("--folha", required=True, help="Folha code (e.g., SB21_ZA_II2_NE)")
    p_run.add_argument("--data-ref", required=False, default=None, help="Reference date YYYY-MM-DD")
    p_run.add_argument("--model", default="rf", help="Model backend (rf|svm|cnn|som)")
    p_run.set_defaults(func=_cmd_run)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
