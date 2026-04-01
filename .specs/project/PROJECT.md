# Preditor Terra — Evolutionary Vision

**Vision:** A shared PostGIS-backed platform where new geological observations and acquisitions continuously improve lithology class probability maps — the **Carta Viva** ("Living Map").

**For:** Geoscientists, researchers, and programmers collaborating on geodata + ML workflows.

**Solves:** Fragmented geodata ingestion and non-reproducible map updates by providing a versioned, folha-driven pipeline that retrains/re-predicts when new data arrives.

---

## Origin & Motivation

The project started in July 2021 as a geophysical data science effort: interpolation scripts for gamaespectrometry data, pandas-based tutorials, and exploratory notebooks aimed at lithological mapping from aerogeophysical surveys. The core question — *can we predict lithology from remote sensing + geophysics?* — has driven every subsequent era of development.

---

## Timeline

| Era | Period | Theme | Key Contribution |
|-----|--------|-------|------------------|
| **1** | Jul–Sep 2021 | Geophysical data science | Interpolation scripts, pandas tutorials, gamaespectrometry processing |
| **2** | Oct 2021–Feb 2023 | Cartographic grid + SOM | `ConstroiFolhas`, `DicionarioFolhas`, geodatabase, SOM classification framework |
| **3** | Mar 2023–Sep 2024 | QGIS plugin + academic | `fonte/mapgeo` plugin, SIICUSP posters/presentations, academic reports |
| **4** | Jul 2025 | Codex modernization | PRs #6-#20: MIT license, env vars, import fixes, deprecated API removal, first test stubs |
| **5** | Nov 2025 | Satellite ML pipeline (terraX) | STAC search, ASTER+Sentinel-2 fusion, CNN training, `full_pipeline.py`, `CODEX.md` design doc |
| **6** | Jan–Feb 2026 | Adaptive loop + vision | `adaptive/` package, PostGIS schema, `.specs/` framework, "Orbis Praedictus" / "Carta Viva" vision |
| **7** | Mar 2026 | Territorial MVP (Gamba) | MCDA plugin, embedded GPKG, pytest suite, QgsTask async, ZIP delivery |

**Conceptual thread:** Data science scripts → Cartographic framework → QGIS tool → Satellite ML pipeline → Adaptive system → Field-ready MVP

---

## Current Vision: Carta Viva

The "Carta Viva" (Living Map) concept, articulated during Era 6, captures the project's long-term ambition: a predictive lithological map that is never final. Each new field observation, each new satellite acquisition, each new geophysical survey refines the probability surface. The map is alive — it learns.

This vision connects all eras:
- **Eras 1-2** built the data foundations (geophysics, cartographic grids, SOM classification)
- **Eras 3-4** made the tools accessible (QGIS plugin, modernized codebase)
- **Era 5** added the satellite ML backbone (STAC → fusion → CNN prediction)
- **Era 6** designed the adaptive loop (new data → retrain → compare → publish)
- **Era 7** delivered a field-testable MVP (territorial MCDA for Gamba fieldwork)

---

## Goals

- [ ] Given a `folha` + `data_ref`, the system generates lithology probability maps (and predicted class map) and stores outputs + metadata in PostgreSQL/PostGIS.
- [ ] When new data is added to the database, the system can rerun the pipeline, compute deltas vs the previous run, and persist evaluation metrics (accuracy, precision/recall, F1, AUC when applicable).

---

## Tech Stack

**Core:**
- Language: Python 3.x
- Database: PostgreSQL + PostGIS
- Geospatial: geopandas, shapely, rasterio, xarray, rioxarray, pyproj
- Remote sensing: STAC via pystac-client (+ planetary-computer signing when needed)
- ML: scikit-learn (RF/SVM), PyTorch (CNNs), sklearn_som (SOM clustering — active since Era 2)
- MCDA: grid-based multicriteria scoring with lithology + occurrence distance (Era 7)
- Plugins: 2 QGIS plugins — `preditor_terra` (SOM/PostGIS-backed) and `preditor_territorial_mvp` (standalone MCDA)

**Existing code reused from this repo (starting point):**
- STAC discovery + scene ranking: `codes/search_pair.py`, `codes/stac_utils.py`
- Raster clipping + cloud/nodata metrics: `codes/raster_utils.py`
- ASTER/S2 fusion + super-cube: `codes/gs_fusion.py`, `codes/supercube.py`
- Label rasterization from PostGIS: `codes/labeling_lito.py`, `codes/db_conn.py`
- Dataset extraction + CNN baseline: `codes/dataset_pixels.py`, `codes/dataset_patches.py`, `codes/train.py`
- Territorial MCDA scoring: `codes/territorial_priority.py`, `codes/territorial_sources.py`

---

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
- Territorial MCDA plugin: standalone QGIS plugin with embedded GPKG, multicriteria scoring, priority classification.
- Distributable ZIP plugin packaging for field deployment.

**Explicitly out of scope (v1):**
- Multi-tenant public web app (auth, permissions, rate limiting).
- Real-time streaming ingestion.
- Distributed training orchestration (Airflow/K8s).
- GAN-based generation workflows.
- Mineral prospectivity (separate target; keep interfaces extensible).

---

## Constraints

- Data heterogeneity: contributions may be sparse, noisy, or inconsistent across regions/CRS/time.
- Compute: raster-based per-folha training/inference can be heavy; v1 targets single-machine runs.
- Reproducibility: outputs must be versioned with deterministic configs and dataset snapshots.
