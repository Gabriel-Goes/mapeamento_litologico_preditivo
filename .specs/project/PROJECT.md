# Preditor Terra Adaptive System (CAS)

**Vision:** A shared PostGIS-backed platform where new geological observations and acquisitions continuously improve lithology class probability maps.
**For:** Geoscientists, researchers, and programmers collaborating on geodata + ML workflows.
**Solves:** Fragmented geodata ingestion and non-reproducible map updates by providing a versioned, folha-driven pipeline that retrains/re-predicts when new data arrives.

## Goals

- [ ] Given a `folha` + `data_ref`, the system generates lithology probability maps (and predicted class map) and stores outputs + metadata in PostgreSQL/PostGIS.
- [ ] When new data is added to the database, the system can rerun the pipeline, compute deltas vs the previous run, and persist evaluation metrics (accuracy, precision/recall, F1, AUC when applicable).

## Tech Stack

**Core:**
- Language: Python 3.x
- Database: PostgreSQL + PostGIS
- Geospatial: geopandas, shapely, rasterio, xarray, rioxarray, pyproj
- Remote sensing: STAC via pystac-client (+ planetary-computer signing when needed)
- ML: scikit-learn (RF/SVM), PyTorch (CNNs), SOM libraries (optional)

**Existing code reused from this repo (starting point):**
- STAC discovery + scene ranking: `codes/search_pair.py`, `codes/stac_utils.py`
- Raster clipping + cloud/nodata metrics: `codes/raster_utils.py`
- ASTER/S2 fusion + super-cube: `codes/gs_fusion.py`, `codes/supercube.py`
- Label rasterization from PostGIS: `codes/labeling_lito.py`, `codes/db_conn.py`
- Dataset extraction + CNN baseline: `codes/dataset_pixels.py`, `codes/dataset_patches.py`, `codes/train.py`

## Scope

**v1 includes:**
- Canonical PostGIS schema for collaborative inputs (points/lines/polygons + attributes + provenance).
- A run-tracking schema for: model version, feature set, training dataset snapshot, metrics, and outputs.
- A CLI-driven pipeline that:
  - reads new/updated data from PostGIS,
  - assembles per-folha training data (labels + feature vectors),
  - trains a baseline classifier (start with RF or SVM; CNN optional),
  - generates per-folha probability rasters, and
  - stores outputs + diffs vs previous runs.
- Minimal configuration system (DB connection, STAC catalogs, output locations).

**Explicitly out of scope (v1):**
- Multi-tenant public web app (auth, permissions, rate limiting).
- Real-time streaming ingestion.
- Distributed training orchestration (Airflow/K8s).
- GAN-based generation workflows.
- Mineral prospectivity (separate target; keep interfaces extensible).

## Constraints

- Data heterogeneity: contributions may be sparse, noisy, or inconsistent across regions/CRS/time.
- Compute: raster-based per-folha training/inference can be heavy; v1 targets single-machine runs.
- Reproducibility: outputs must be versioned with deterministic configs and dataset snapshots.
