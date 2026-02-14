# External Integrations

## PostgreSQL / PostGIS
- **Purpose:** Geometry boundaries (`carto.folhas_cartograficas`) and lithology polygons (`litologia.litologia_100k`) are the ground truth for every predictive map.
- **Implementation:** `codes/db_conn.py` builds a SQLAlchemy `Engine` (`get_engine`) and exposes `get_folha_geom_geojson` plus `get_litologia_100k_for_folha`. `labeling_lito` rasterizes the resulting `GeoDataFrame` in the super-cube CRS.
- **Configuration:** Connection strings come from environment variables read in `codes/config.py` (`PG_USER`, `PG_PASS`, `PG_HOST`, etc.).

## STAC catalogs via Microsoft Planetary Computer
- **Purpose:** Acquire ASTER L1T and Sentinel-2 L2A imagery covering the target folha.
- **Implementation:** `codes/stac_utils.py` opens STAC clients with `pystac_client` and `planetary_computer.sign_inplace`. `codes/search_pair` orchestrates ASTER/Sentinel-2 queries, while `codes/aster_pipeline.py` surfaces ranking + CSV/JSON exports.
- **Authentication:** `planetary_computer` signs requests automatically when `planetarycomputer` appears in the STAC URL; downloaded assets may also be cached locally (`raster_utils.download_pc_asset_to_local`).

## QGIS / PyQt
- **Purpose:** Provide an in-software UI for previewing datasets, executing SOM/SVM workflows, and inspecting metadata.
- **Implementation:** `codes/PreditorTerra_Final.py` imports `qgis.PyQt`, `qgis.core`, and instantiates widgets, shader renderers, and message bars; `PreditorTerra_qgis.py` and `PreditorTerraQGIS.py` are alternate QGIS entry points.
- **Execution:** Scripts run inside the QGIS Python console (`iface` is imported from `qgis.utils`). They rely on the underlying QGIS project to host raster layers.

## Raster storage / caching
- **Purpose:** Super-cube outputs, fused rasters, and cached STAC assets are written to disk for repeated analysis.
- **Implementation:** `ORBITAL_DIR` (expected to be configured via `codes/config.py`, though the current file only shows PostgreSQL details) is used by `gs_fusion`, `supercube`, and `raster_utils` to store `*.tif` and `.meta.json` artifacts.
- **Caching:** `raster_utils.download_pc_asset_to_local` persists downloaded STAC assets under `PC_CACHE_DIR` (also expected to be configured in `config.py`).

## Logging
- **Service:** Local log files (`logs/preditor_terra*.log`) are written using `codes/log_utils.py`; no remote logging services are in use.
