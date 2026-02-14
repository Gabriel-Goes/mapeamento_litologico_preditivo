# Adaptive Loop Tasks

## Phase A - Make the Existing Pipeline Runnable (Prereq)

- [x] Unify configuration for STAC + outputs in `codes/config.py` (add `PC_STAC_URL`, `ORBITAL_DIR`, `PC_CACHE_DIR`, `DEFAULT_STAC_CATALOGS`, `load_stac_catalog_config`).
- [ ] Add `codes/doctor.py` to validate:
  - DB connectivity and required tables (`carto.folhas_cartograficas`, `litologia.litologia_100k`)
  - STAC reachability
  - write access to `ORBITAL_DIR`
  - dependencies (`pystac_client`, `planetary_computer`, `rioxarray`)
  - Verification: `python codes/doctor.py` exits 0 and prints a checklist.

## Phase B - PostGIS Schema for Adaptive Loop

- [x] Add `sql/adaptive_schema.sql` with:
  - `contrib.observations`, `contrib.acquisitions`
  - `ml.run`, `ml.metric`, `ml.artifact`, `ml.run_compare`
  - indexes on `geom`, `folha_codigo`, timestamps
  - Verification: schema applies cleanly on an empty database.

- [x] Add `adaptive/db.py` (engine + helpers) reusing env vars from `codes/config.py`.
  - Verification: `python -c "from adaptive.db import get_engine"` works.

- [x] Add `adaptive/settings.py` (env-driven settings + validation).
  - Verification: `python -c "from adaptive.settings import Settings; Settings.from_env()"` works.

## Phase C - Dataset Snapshot + Ingestion

- [ ] Implement `adaptive/ingest/observations.py`:
  - query observations for a folha
  - validate geometry and required fields
  - deterministic conflict resolution
  - Verification: unit-level run on a small seeded dataset returns counts + errors.

- [ ] Implement `adaptive/datasets/snapshot.py`:
  - compute a stable `dataset_hash` from source table rows + config
  - write snapshot metadata to DB
  - Verification: same inputs produce same hash.

## Phase D - Baseline Model + Raster Outputs

- [ ] Implement `adaptive/models/rf.py` (RandomForestClassifier):
  - fit + predict_proba
  - persist model artifact (joblib)
  - Verification: trains on a small dataset and predicts probabilities.

- [ ] Implement `adaptive/maps/rasterize.py`:
  - reshape super-cube `(C,H,W)` -> `(H*W,C)` with nodata mask
  - write predicted class + probability cube to GeoTIFF
  - Verification: output GeoTIFFs open in rasterio/QGIS and have expected CRS/shape.

## Phase E - Orchestrator + CLI

- [ ] Implement `adaptive/pipeline/run.py`:
  - create `ml.run` row (running)
  - call imagery selection/supercube builder from existing `codes/*`
  - assemble labels + features
  - train model backend
  - write artifacts + metrics
  - compare with previous run
  - update `ml.run` (succeeded/failed)
  - Verification: `adaptive` pipeline produces DB rows + GeoTIFF artifacts end-to-end for one folha.

- [x] Implement initial `adaptive/cli.py` scaffolding:
  - `init-db` applies schema
  - `doctor` checks DB connectivity
  - Verification: `python -m adaptive.cli --help` works.

- [ ] Extend `adaptive/cli.py` to support the full MVP surface:
  - `run --folha --data-ref [--model rf]` (real run, not stub)
  - `compare --folha --run-id`
  - Verification: `python -m adaptive.cli run ...` executes end-to-end and prints run_id.

## Phase F - Documentation

- [ ] Add `docs/adaptive_loop.md` describing:
  - required PostGIS tables
  - config (env vars)
  - example commands
  - Verification: a new user can run one folha with only docs.
