# Adaptive Loop Design

## Overview

This repo already contains strong building blocks for a folha-driven imagery pipeline (STAC search, cloud/nodata checks, ASTER/S2 fusion, super-cube creation, and dataset extraction). The missing piece for a "complex adaptive system" is a reproducible control loop around:

- ingesting new data from PostGIS,
- snapshotting datasets,
- training/predicting with a selected model backend,
- persisting outputs and metrics, and
- comparing new outputs against previous runs.

The design below keeps v1 pragmatic: a CLI orchestrator and a PostGIS schema for inputs and run tracking. UI and automation (QGIS plugin, LISTEN/NOTIFY) are layered later.

## Key Design Decisions

- **Folha-centric execution:** every run is keyed by `folha_codigo` and optional `data_ref`.
- **Artifact storage:** store rasters as GeoTIFF files and reference them from DB.
- **Pluggable pipelines:** define interfaces for feature extractors and model backends.

## Proposed Modules (new)

Create a new, clean namespace (to avoid refactoring all legacy scripts immediately):

- `adaptive/` (new package)
  - `settings.py`: reads env/config; validates required settings.
  - `db.py`: SQLAlchemy engine + helpers.
  - `cli.py`: command-line entrypoint.
  - `ingest/observations.py`: validation + ingestion queries.
  - `features/`: feature extraction/adapters.
  - `models/`: backend interface + implementations.
  - `pipeline/run.py`: orchestrator.
  - `datasets/`: dataset snapshot + assembly.

- `sql/adaptive_schema.sql`: canonical tables for contributions + runs.

Existing code reused via imports:
- STAC + imagery quality: `codes/search_pair.py`, `codes/raster_utils.py`, `codes/stac_utils.py`
- Fusion/supercube: `codes/gs_fusion.py`, `codes/supercube.py`
- Labels + dataset: `codes/labeling_lito.py`, `codes/dataset_pixels.py`, `codes/dataset_patches.py`

## Database Schema (v1)

### 1) Collaborative inputs

- `contrib.observations`
  - `id` (pk)
  - `geom` (geometry; point/line/polygon)
  - `folha_codigo` (text; optional but recommended)
  - `label` (int or text; lithology class)
  - `confidence` (float 0..1)
  - `source` (text; e.g., "field", "map_100k", "paper")
  - `attrs` (jsonb; flexible attributes)
  - `created_at`, `updated_at`

- `contrib.acquisitions`
  - `id` (pk)
  - `kind` (text; e.g., "mag", "gamma", "stac_scene")
  - `geom` (geometry footprint or sampling geometry)
  - `time_start`, `time_end`
  - `attrs` (jsonb; units, sensor, etc.)
  - `created_at`, `updated_at`

### 2) Run tracking

- `ml.run`
  - `id` (pk)
  - `folha_codigo`
  - `data_ref`
  - `status` (pending/running/succeeded/failed)
  - `config_json` (jsonb)
  - `dataset_hash` (text)
  - `model_backend` (text)
  - `model_params` (jsonb)
  - `started_at`, `finished_at`
  - `error_message`

- `ml.metric`
  - `id` (pk)
  - `run_id` (fk)
  - `name` (text)  # e.g., accuracy, f1_macro
  - `value` (double)

- `ml.artifact`
  - `id` (pk)
  - `run_id` (fk)
  - `kind` (text)  # predicted_class, prob_cube, report_json
  - `uri` (text)   # filesystem path or object storage URI
  - `checksum` (text)
  - `attrs` (jsonb) # CRS, bbox, nodata, bands, etc.

- `ml.run_compare`
  - `id` (pk)
  - `run_id_new` (fk)
  - `run_id_prev` (fk)
  - `summary` (jsonb) # metric deltas, change stats

This schema is intentionally minimal; it can evolve into Alembic migrations later.

## Pipeline Steps (v1)

1. **Resolve folha geometry** from PostGIS (`carto.folhas_cartograficas`).
2. **Assemble training labels**:
   - rasterize lithology polygons (`litologia.litologia_100k`) as baseline labels,
   - optionally enrich with contributor observations (priority/confidence rules).
3. **Assemble features**:
   - imagery: select ASTER + S2 scenes via STAC; enforce coverage and cloud-free; build super-cube.
   - (optional) geophysics: join point surveys to the folha grid or sample at label points.
4. **Train model backend**:
   - v1 baseline: RandomForest or SVM on per-pixel spectral vectors; CNN optional.
5. **Predict**:
   - predicted class raster + per-class probability rasters (or a multi-band cube).
6. **Persist**:
   - write GeoTIFF(s) to `ORBITAL_DIR` (or a configured artifacts dir),
   - insert `ml.run`, `ml.metric`, `ml.artifact` rows.
7. **Compare with previous run**:
   - compute metric deltas,
   - compute change stats on predicted class (area changed, per-class deltas),
   - store `ml.run_compare`.

## Model Backend Interface (v1)

Define a small interface so new models can be added without changing the orchestrator:

- `fit(X_train, y_train, **params) -> model`
- `predict_proba(model, X) -> probs`
- `predict(model, X) -> y_pred`

For raster prediction, `X` is created by reshaping the super-cube into `(H*W, C)` and masking nodata.

## Observability

- Structured logs per run (stdout + file).
- DB stores error messages, run durations, and a minimal report JSON artifact.
