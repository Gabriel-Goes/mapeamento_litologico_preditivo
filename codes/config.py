from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

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

STAC_CATALOGS_FILE: str | None = os.getenv("STAC_CATALOGS_FILE")

DEFAULT_STAC_CATALOGS: Dict[str, List[Dict[str, Any]]] = {
    "aster": [
        {
            "name": "ASTER AST_L1T (Planetary Computer)",
            "url": PC_STAC_URL,
            "collections": ["aster-l1t"],
            "processing_level": "L1T",
            "priority": 1,
            "preferred_assets": ["VNIR", "SWIR"],
            "cloudmask_assets": ["CLOUDMASK", "QA", "CLOUD"],
            "notes": "Coleção padrão assinada automaticamente pelo Planetary Computer.",
        },
        {
            "name": "ASTER AST_L1T (NASA LPCLOUD)",
            "url": "https://cmr.earthdata.nasa.gov/stac/LPCLOUD",
            "collections": ["AST_L1T_003"],
            "processing_level": "L1T",
            "priority": 2,
            "preferred_assets": ["VNIR", "SWIR"],
            "cloudmask_assets": ["CLOUD", "QA", "CLOUDMASK"],
            "notes": "Fallback com Earthdata; manter VNIR/SWIR e máscara QA explícita.",
        },
    ],
    "sentinel2": [
        {
            "name": "Sentinel-2 L2A (Planetary Computer)",
            "url": PC_STAC_URL,
            "collections": ["sentinel-2-l2a"],
            "processing_level": "L2A",
            "priority": 1,
            "cloudmask_assets": ["SCL"],
            "notes": "Coleção L2A padrão assinada pelo Planetary Computer.",
        }
    ],
}


def load_stac_catalog_config() -> Dict[str, List[Dict[str, Any]]]:
    """Carrega a lista de catálogos STAC preferenciais.

    A configuração pode ser sobrescrita via variável de ambiente
    ``STAC_CATALOGS_FILE`` apontando para um JSON ou YAML. Se não houver
    override, retorna ``DEFAULT_STAC_CATALOGS``.
    """

    if not STAC_CATALOGS_FILE:
        return DEFAULT_STAC_CATALOGS

    cfg_path = Path(STAC_CATALOGS_FILE)
    if not cfg_path.exists():
        raise FileNotFoundError(f"STAC_CATALOGS_FILE não encontrado: {cfg_path}")

    if cfg_path.suffix.lower() in {".yml", ".yaml"}:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover - dependência opcional
            raise RuntimeError(
                "PyYAML é necessário para ler arquivos YAML de catálogos STAC. "
                "Instale com `pip install pyyaml` ou use JSON."
            ) from exc

        with cfg_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    else:
        with cfg_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Arquivo de catálogos STAC deve conter um objeto na raiz.")

    return data  # type: ignore[return-value]
