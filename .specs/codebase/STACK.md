# Tech Stack

**Analyzed:** February 14, 2026

## Core
- **Language:** Python 3.x (CPython) – scripts rely on f-strings, dataclasses hints and `__future__` annotations.
- **Runtime:** Standalone command-line scripts and QGIS plugins executed inside QGIS/PyQt environments.
- **Package managers:** `conda` (via `dotfiles/environment.yml`) to install geospatial/ML stacks and `pip` for extras (`rasterio`, `vert`, `scikit-learn`, `torch`).

## Frontend/UI
- **UI framework:** PyQt/QGIS (`qgis.PyQt`, `qgis.core`) – `codes/PreditorTerra_Final.py` builds the custom QGIS dock/widget.
- **Visualization:** `matplotlib` (plots integrated within QGIS or standalone), `verde`/`rioxarray` for raster rendering of previews.
- **State:** Global dictionaries (e.g., `som_store`, `bdc_items`) maintained in scripts rather than external state management.

## Backend/Data Processing
- **Data access:** PostgreSQL/PostGIS via `codes/db_conn.py` and `SQLAlchemy` engines (`create_engine`, `text`).
- **Geospatial stack:** `geopandas`, `shapely`, `pyproj`, `rasterio`, `xarray`, `rioxarray`, `fiona` and hydro-specific `verde` for interpolation.
- **Raster/array utilities:** Custom helpers (`codes/raster_utils.py`, `codes/supercube.py`, `codes/gs_fusion.py`) rely on `numpy`, `osgeo`, `gdal`, `requests` and `tqdm` for downloads.

## Machine learning
- **Deep learning:** PyTorch (`torch`, `torch.nn`, `DataLoader`, CUDA-aware device selection) used in `codes/train.py`, `models_cnn.py`, and `torch_datasets.py` for pixel/patch classifiers.
- **Classical ML:** scikit-learn (`sklearn.metrics`, `sklearn.preprocessing`) plus the third-party `sklearn_som` for prototype SOM workflows.
- **Data wrangling:** `pandas` for tabular logging and `numpy` for numerical operations.

## Spatial/Remote sensing integrations
- **STAC client:** `pystac_client` + `planetary_computer` for signed access to Microsoft Planetary Computer catalogs (see `codes/stac_utils.py`).
- **Asset fusion:** Gram-Schmidt fusion routines (`codes/gs_fusion.py`) combine ASTER VNIR/SWIR with Sentinel-2 PAN bands.

## Testing & Tools
- **Testing frameworks:** Not defined; experimentation happens via scripts/notebooks (no automated test suite discovered).
- **Dev tooling:** `conda` environments via `dotfiles/environment.yml`, `install.sh` bootstraps the virtualenv, and numerous Jupyter notebooks under `jupyternotebooks/` and `candidatos_orbitais/` for exploratory work.
- **Logging:** `codes/log_utils.py` writes to `logs/preditor_terra*.log` for manual inspection.

## External services
- **Planetary Computer STAC:** STAC searches/dataset downloads rely on Azure-hosted catalogs (`PC_STAC_URL`) with caching helpers (`raster_utils.download_pc_asset_to_local`).
- **PostgreSQL/PostGIS:** geometry/lithology tables (`carto.folhas_cartograficas`, `litologia.litologia_100k`) provide spatial context for each folha via `db_conn`.
- **QGIS GUI environment:** The `PreditorTerra_*` scripts are executed in the QGIS Python console, so PyQt bindings and QGIS project APIs are prerequisites.
