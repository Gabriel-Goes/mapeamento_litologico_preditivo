from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Runtime configuration for the adaptive loop.

    v1 keeps this simple and environment-variable driven.
    """

    pg_conn_str: str
    orbital_dir: Path
    artifacts_dir: Path
    stac_catalogs_file: str | None

    @staticmethod
    def from_env() -> "Settings":
        # Reuse repo defaults from codes/config.py when available.
        try:
            from codes import config as repo_config

            pg_conn_str = os.getenv("PG_CONN_STR", repo_config.PG_CONN_STR)
            orbital_dir = Path(os.getenv("ORBITAL_DIR", repo_config.ORBITAL_DIR))
        except Exception:
            # Fallback for minimal installs.
            pg_conn_str = os.getenv("PG_CONN_STR", "")
            orbital_dir = Path(os.getenv("ORBITAL_DIR", "./artifacts")).resolve()

        artifacts_dir = Path(os.getenv("ARTIFACTS_DIR", str(orbital_dir / "adaptive_artifacts"))).resolve()
        stac_catalogs_file = os.getenv("STAC_CATALOGS_FILE")

        return Settings(
            pg_conn_str=pg_conn_str,
            orbital_dir=orbital_dir,
            artifacts_dir=artifacts_dir,
            stac_catalogs_file=stac_catalogs_file,
        )

    def validate(self) -> None:
        if not self.pg_conn_str:
            raise RuntimeError(
                "Missing PG connection string. Set PG_USER/PG_PASS/PG_HOST/PG_PORT/PG_DB (or PG_CONN_STR)."
            )

        # Don't create dirs on import; do it on validate/run.
        self.orbital_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
