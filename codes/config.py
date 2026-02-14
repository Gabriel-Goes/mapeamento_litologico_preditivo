from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

# Optional dependency; only needed when the user points STAC_CATALOGS_FILE to YAML.
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

# -----------------------------------------------------------------------------
# PostgreSQL / PostGIS
# -----------------------------------------------------------------------------

PG_USER: str = os.getenv("PG_USER", "postgres")
PG_PASS: str = os.getenv("PG_PASS", "postgres")
PG_HOST: str = os.getenv("PG_HOST", "localhost")
PG_PORT: str = os.getenv("PG_PORT", "5432")
PG_DB: str = os.getenv("PG_DB", "geologia")

PG_CONN_STR: str = f"postgresql+psycopg2://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"

# -----------------------------------------------------------------------------
# Paths / outputs
# -----------------------------------------------------------------------------

_CODES_DIR = Path(__file__).resolve().parent
ORBITAL_DIR: str = os.getenv("ORBITAL_DIR", str(_CODES_DIR / "recortes_orbitais"))
PC_CACHE_DIR: str = os.getenv("PC_CACHE_DIR", str(Path(ORBITAL_DIR) / "pc_cache"))

# -----------------------------------------------------------------------------
# STAC catalogs (ASTER + Sentinel-2)
# -----------------------------------------------------------------------------

PC_STAC_URL: str = os.getenv("PC_STAC_URL", "https://planetarycomputer.microsoft.com/api/stac/v1")

# Repo-wide default catalogs. Users can override by setting STAC_CATALOGS_FILE to
# a JSON/YAML file (see load_stac_catalog_config()).
DEFAULT_STAC_CATALOGS: Dict[str, List[Dict[str, Any]]] = {
    "aster": [
        {
            "name": "ASTER L1T (Planetary Computer)",
            "url": PC_STAC_URL,
            "collections": ["aster-l1t"],
            "priority": 1,
            "preferred_assets": ["VNIR", "SWIR"],
            "cloudmask_assets": ["CLOUDMASK", "QA", "CLOUD"],
        }
    ],
    "sentinel2": [
        {
            "name": "Sentinel-2 L2A (Planetary Computer)",
            "url": PC_STAC_URL,
            "collections": ["sentinel-2-l2a"],
            "priority": 1,
        }
    ],
}


def load_stac_catalog_config(
    path: str | None = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Load STAC catalog configuration.

    Order of precedence:
    1. explicit `path`
    2. env var STAC_CATALOGS_FILE
    3. DEFAULT_STAC_CATALOGS
    """

    cfg_path = path or os.getenv("STAC_CATALOGS_FILE")
    if not cfg_path:
        return DEFAULT_STAC_CATALOGS

    p = Path(cfg_path)
    if not p.exists():
        raise FileNotFoundError(f"STAC_CATALOGS_FILE not found: {p}")

    raw = p.read_text(encoding="utf-8")
    suffix = p.suffix.lower()

    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError(
                "PyYAML is required to parse YAML STAC catalogs. Install `pyyaml` "
                "or use a JSON config file."
            )
        data = yaml.safe_load(raw)
    else:
        data = json.loads(raw)

    if not isinstance(data, dict):
        raise ValueError("STAC catalog config must be a mapping like {'aster': [...], 'sentinel2': [...]} .")

    # Shallow validation to help fail fast.
    for key in ("aster", "sentinel2"):
        if key in data and not isinstance(data[key], list):
            raise ValueError(f"STAC catalog config for '{key}' must be a list.")

    return data
