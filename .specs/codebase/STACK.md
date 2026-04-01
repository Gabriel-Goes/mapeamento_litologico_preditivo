# Tech Stack

**Analyzed:** March 18, 2026

## Core

- **Language:** Python 3.x (CPython) – scripts rely on f-strings, dataclasses, and `__future__` annotations.
- **Runtime:** Three surfaces: standalone CLI scripts (system Python), QGIS plugins (QGIS Python), and Jupyter notebooks.
- **Package managers:** `conda` (via `dotfiles/environment.yml`) for geospatial/ML stacks; `pip` for extras.

## Frontend/UI

- **UI framework:** PyQt/QGIS (`qgis.PyQt`, `qgis.core`) [Era 2→7] — two plugins and a consolidated dock widget.
- **QgsTask:** [Era 7] Background task execution for long-running MCDA operations; keeps QGIS responsive.
- **Visualization:** `matplotlib` [Era 1+] for plots; `verde`/`rioxarray` for raster rendering.
- **State:** Global dictionaries (e.g., `som_store`, `bdc_items`) in scripts; no external state management.

## Backend/Data Processing

- **PostgreSQL/PostGIS:** [Era 3→6] Geometry boundaries, lithology polygons, adaptive loop schema.
- **SQLAlchemy:** [Era 3] `create_engine` + `text` for DB access in `codes/db_conn.py`.
- **psycopg2:** [Era 6] Fallback driver in `adaptive/db.py` when SQLAlchemy is unavailable.
- **GeoPackage:** [Era 7] Embedded spatial data in `preditor_territorial_mvp/data/` — self-contained, no DB required.
- **ogr2ogr:** [Era 7] Used in `scripts/build_gamba_mvp_data.sh` for PostGIS → GPKG extraction.
- **Geospatial stack:** `geopandas` [Era 1+], `shapely` [Era 1+], `pyproj` [Era 1+], `rasterio` [Era 5], `xarray`/`rioxarray` [Era 5], `fiona` [Era 5], `verde` [Era 1] for interpolation.
- **Raster/array utilities:** `numpy` [Era 1+], `osgeo`/`gdal` [Era 2+], `requests` [Era 5], `tqdm` [Era 5] for downloads.

## Machine Learning

- **Deep learning:** PyTorch [Era 5] (`torch`, `torch.nn`, `DataLoader`, CUDA-aware device selection) — pixel/patch CNN classifiers.
- **Classical ML:** scikit-learn [Era 2+] (`sklearn.metrics`, `sklearn.preprocessing`).
- **SOM:** `sklearn_som` [Era 2, active in Era 5+] for unsupervised lithology clustering in QGIS dock.
- **Data wrangling:** `pandas` [Era 1+] for tabular operations; `numpy` [Era 1+] for numerical.

## Spatial/Remote Sensing Integrations

- **STAC client:** `pystac_client` [Era 5] + `planetary_computer` for signed access to Microsoft Planetary Computer.
- **BDC STAC:** [Era 5] Brazil Data Cube catalog access via `codes/bdc_qgis_search.py`.
- **Asset fusion:** Gram-Schmidt routines [Era 5] in `codes/gs_fusion.py` combine ASTER VNIR/SWIR with Sentinel-2 PAN bands.

## MCDA

- **Grid-based scoring:** [Era 7] Lithology scoring + mineral occurrence distance, with restriction/slope masks.
- **Priority classification:** [Era 7] 4 classes output as rasters + JSON summary report.

## Testing & Tools

- **pytest:** [Era 7] Test framework with synthetic geometry fixtures (`tests/test_territorial_priority.py`, `tests/test_mvp_mcda_engine.py`).
- **First test stubs:** [Era 4] `tests/test_database.py`, `fonte/mapgeo/test/` (PR #14).
- **CI:** Not configured — tests run manually.
- **Dev tooling:** `conda` environments via `dotfiles/environment.yml`; operational scripts in `scripts/`.
- **Logging:** `codes/log_utils.py` [Era 5] writes to `logs/preditor_terra*.log`; `QgsMessageLog` [Era 7] for plugin logging.

## External Services

- **Planetary Computer STAC:** [Era 5] Azure-hosted STAC catalogs (`PC_STAC_URL`) with caching.
- **BDC STAC:** [Era 5] Brazil Data Cube for Landsat/CBERS imagery.
- **PostgreSQL/PostGIS:** [Era 3→6] Geometry/lithology tables, adaptive loop schema. Access via SSH tunnel on port 62222.
- **QGIS:** [Era 2→7] Host environment for both plugins and the consolidated dock widget.
