from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pytest

gpd = pytest.importorskip("geopandas")
from shapely.geometry import Point, Polygon

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = REPO_ROOT / "plugins" / "preditor_territorial_mvp"
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from mcda_engine import list_available_folhas, run_mcda_from_gpkg


def _write_test_gpkg(gpkg_path: Path) -> None:
    crs = "EPSG:32721"
    folha_geom = Polygon(
        [
            (500000.0, 9200000.0),
            (501000.0, 9200000.0),
            (501000.0, 9201000.0),
            (500000.0, 9201000.0),
            (500000.0, 9200000.0),
        ]
    )

    mc = gpd.GeoDataFrame(
        {"id_folha": ["TEST_FOLHA"], "EPSG": [32721]},
        geometry=[folha_geom],
        crs=crs,
    )

    # Cobre somente metade da folha para garantir area restrita.
    litologia_geom = Polygon(
        [
            (500000.0, 9200000.0),
            (500500.0, 9200000.0),
            (500500.0, 9201000.0),
            (500000.0, 9201000.0),
            (500000.0, 9200000.0),
        ]
    )
    litologia = gpd.GeoDataFrame(
        {"LITOTIPOS": ["xisto grafitoso"]},
        geometry=[litologia_geom],
        crs=crs,
    )

    ocorr = gpd.GeoDataFrame(
        {"SUBSTANCIA": ["grafita"]},
        geometry=[Point(500250.0, 9200500.0)],
        crs=crs,
    )

    mc.to_file(gpkg_path, layer="mc_100k", driver="GPKG")
    litologia.to_file(gpkg_path, layer="litologia_100k", driver="GPKG")
    ocorr.to_file(gpkg_path, layer="ocorr_min_cprm", driver="GPKG")


def test_list_available_folhas(tmp_path: Path) -> None:
    gpkg_path = tmp_path / "mvp.gpkg"
    _write_test_gpkg(gpkg_path)

    folhas = list_available_folhas(gpkg_path)
    assert folhas == ["TEST_FOLHA"]


def test_run_mcda_from_gpkg_generates_priority_with_restrictions(tmp_path: Path) -> None:
    gpkg_path = tmp_path / "mvp.gpkg"
    _write_test_gpkg(gpkg_path)

    result = run_mcda_from_gpkg(
        gpkg_path=gpkg_path,
        folha_codigo="TEST_FOLHA",
        pixel_size_m=200,
        low_threshold=0.4,
        high_threshold=0.7,
    )

    assert result.epsg == 32721
    assert result.pixel_size_m == 200
    assert result.potential.shape == result.restriction.shape == result.priority.shape
    assert result.potential.ndim == 2
    assert result.potential.size > 0

    restricted_mask = result.restriction.astype(bool)
    assert restricted_mask.any()
    assert np.all(result.priority[restricted_mask] == 1)

    valid_classes = set(np.unique(result.priority).tolist())
    assert valid_classes.issubset({0, 1, 2, 3, 4})

    assert result.metadata["folha_codigo"] == "TEST_FOLHA"
    assert result.metadata["inputs"]["litologia_features"] == 1
    assert result.metadata["inputs"]["ocorrencias_features"] == 1
