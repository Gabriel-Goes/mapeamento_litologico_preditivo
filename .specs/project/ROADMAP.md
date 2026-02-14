# Roadmap

**Current Milestone:** M1 - Adaptive Loop MVP (DB ingest -> train -> predict -> store -> compare)
**Status:** Planning

---

## M0 - Boilerplate Hardening

**Goal:** Make the existing repo runnable as a reliable starting point (config + reproducibility).
**Target:** Repo can run STAC selection + super-cube generation end-to-end with documented config.

### Features

**Configuration Unification** - COMPLETE
- Centralize DB + STAC + output path configuration in `codes/config.py`.
- Support `STAC_CATALOGS_FILE` override for catalog endpoints.

**Minimal CLI Health Checks** - PLANNED
- Add a `codes/doctor.py` that validates DB connectivity, required tables, STAC reachability, and writable output dirs.

---

## M1 - Adaptive Loop MVP

**Goal:** A reproducible, folha-driven pipeline that updates predictions when new data appears.

### Features

**Collaborative Data Schema** - IN PROGRESS
- Tables for user contributions (points/lines/polygons) + attributes + provenance.
- Tables for acquisition measurements (e.g., magnetometry, gamma spectrometry) with time and units.

**Run Tracking + Versioning** - IN PROGRESS
- Tables for `run`, `model_version`, `dataset_snapshot`, `metrics`, `output_artifacts`.

**Baseline Model + Probability Maps** - PLANNED
- Train baseline classifier (RF/SVM) from assembled training dataset.
- Generate per-folha probability maps + predicted class raster.

**Compare Runs** - PLANNED
- Store diff rasters/stats vs previous run for the same folha.
- Persist metrics and model/data lineage.

---

## M2 - Multi-Source Feature Assembly

**Goal:** Expand feature extraction beyond the current ASTER/Sentinel super-cube.

### Features

**Geophysics Feature Joiners** - PLANNED
- Merge point-sampled surveys into folha grids or feature vectors.
- Standardize units and CRS.

**STAC Imagery Extensions** - PLANNED
- Support alternative providers/collections beyond Planetary Computer.
- Add per-provider asset selection rules in config.

---

## M3 - Automation + Interfaces

**Goal:** Make updates continuous and easier for non-programmers.

### Features

**Event Triggering** - PLANNED
- Postgres LISTEN/NOTIFY or polling to detect new contributions.
- Job queue runner for scheduled re-trains.

**QGIS Integration** - PLANNED
- Publish results as PostGIS layers and/or add output rasters to QGIS projects.

---

## Future Considerations

- Add CNN training as a first-class model option.
- Add SOM workflows for unsupervised clustering and label bootstrapping.
- Add mineral prospectivity maps (separate output type, same ingestion/versioning backbone).
