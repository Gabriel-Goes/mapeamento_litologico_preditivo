from __future__ import annotations

import os

PC_STAC_URL: str = os.getenv(
    "PC_STAC_URL",
    "https://planetarycomputer.microsoft.com/api/stac/v1",
)

PG_USER: str = os.getenv("PG_USER", "postgres")
PG_PASS: str = os.getenv("PG_PASS", "postgres")
PG_HOST: str = os.getenv("PG_HOST", "localhost")
PG_PORT: str = os.getenv("PG_PORT", "5432")
PG_DB: str = os.getenv("PG_DB", "geologia")

PG_CONN_STR: str = (
    f"postgresql+psycopg2://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"
)

ORBITAL_DIR: str = os.getenv("ORBITAL_DIR", "./recortes_orbitais")
PC_CACHE_DIR: str = os.getenv("PC_CACHE_DIR", "./pc_cache")
