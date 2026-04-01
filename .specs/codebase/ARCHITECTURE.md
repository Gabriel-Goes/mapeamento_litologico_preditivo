# Architecture — Layered Evolution

The architecture of Preditor Terra is not a designed-from-scratch system — it is an accumulation of 7 eras of development, each adding capabilities on top of the previous. Understanding the layers is essential for navigating the codebase.

---

## Architectural Layers (chronological)

### Layer 1: Data Foundations (Era 1-2, Jul 2021 – Feb 2023)

The earliest layer: geophysical data processing and a cartographic grid system.

- **Geophysical processing:** pandas-based interpolation of gamaespectrometry data, `verde` gridding
- **Cartographic grid:** `ConstroiFolhas` / `DicionarioFolhas` — the folha-based spatial indexing that still underpins all pipeline operations
- **SOM classification:** Self-Organizing Maps for unsupervised lithology clustering (`sklearn_som`)
- **Storage:** GeoPackage and early PostGIS tables (`carto.folhas_cartograficas`, `litologia.litologia_100k`)
- **Key files:** `fonte/mapgeo/nucleo/`, early `codes/` scripts, `jupyternotebooks/`

### Layer 2: QGIS Integration (Era 3-4, Mar 2023 – Jul 2025)

Made the data science accessible through a QGIS plugin, then modernized the codebase.

- **Plugin architecture:** `classFactory` pattern, `QDockWidget` UI, PyQt bindings
- **PostGIS connectivity:** SQLAlchemy engine via `codes/db_conn.py`
- **Academic output:** SIICUSP posters, reports, UML diagrams
- **Codex modernization (Era 4):** MIT license, env vars replacing hardcoded paths, deprecated API fixes, first test stubs
- **Key files:** `fonte/mapgeo/mapgeo.py`, `codes/db_conn.py`, `codes/PreditorTerra_Final.py`

### Layer 3: Satellite ML Pipeline (Era 5, Nov 2025)

The terraX pipeline: a full STAC-to-prediction workflow for lithological mapping.

- **STAC search + scene ranking:** Multi-catalog search (Planetary Computer, BDC) with coverage/cloud/temporal filters
- **Gram-Schmidt fusion:** ASTER VNIR/SWIR fused with Sentinel-2 PAN bands
- **Super-cube construction:** Stacked multi-sensor raster for ML input
- **Dataset extraction:** Pixel-level and patch-level datasets from super-cube + label raster
- **CNN training:** PyTorch pixel/patch classifiers with CUDA support
- **Full pipeline orchestration:** `full_pipeline.py` chains selection → fusion → dataset → training
- **Design document:** `CODEX.md` captures the complete pipeline design
- **Key files:** `codes/search_pair.py`, `codes/gs_fusion.py`, `codes/supercube.py`, `codes/dataset_pixels.py`, `codes/dataset_patches.py`, `codes/train.py`, `codes/models_cnn.py`, `codes/full_pipeline.py`

### Layer 4: Adaptive System (Era 6, Jan–Feb 2026)

Formal specifications and infrastructure for continuous re-prediction.

- **Specs framework:** `.specs/` with PROJECT, ARCHITECTURE, ROADMAP, feature specs
- **PostGIS schema:** `sql/adaptive_schema.sql` for collaborative observations + ML run tracking
- **CLI:** `adaptive/cli.py` with `doctor`, `init-db`, `run` commands (scaffold)
- **DB abstraction:** `adaptive/db.py` with SQLAlchemy → psycopg2 fallback for resilience
- **Settings:** `adaptive/settings.py` — `@dataclass` configuration from environment variables
- **Vision:** "Orbis Praedictus" / "Carta Viva" — the living map concept
- **Key files:** `adaptive/cli.py`, `adaptive/db.py`, `adaptive/settings.py`, `sql/adaptive_schema.sql`

### Layer 5: Territorial MCDA (Era 7, Mar 2026)

A field-ready MVP plugin for territorial priority mapping.

- **Standalone QGIS plugin:** `preditor_territorial_mvp/` with embedded GPKG (no external DB required)
- **MCDA scoring:** Grid-based multicriteria analysis — lithology scoring + mineral occurrence distance
- **Priority classification:** 4 priority classes with restriction masks (conservation units) and slope constraints
- **QgsTask pattern:** Async background processing keeps QGIS responsive during heavy operations
- **pytest suite:** First formal tests — synthetic geometry fixtures, MCDA engine validation
- **ZIP delivery:** Distributable plugin package for field deployment
- **Key files:** `plugins/preditor_territorial_mvp/*`, `codes/territorial_priority.py`, `codes/territorial_sources.py`, `tests/test_territorial_priority.py`, `tests/test_mvp_mcda_engine.py`

---

## Current Data Flows

### STAC → Fusion → ML Flow (Layer 3)

```
PostGIS (folha geometry + lithology)
  ↓
STAC search (Planetary Computer / BDC)
  → ASTER L1T/07/07XT scene selection
  → Sentinel-2 L2A scene selection
  ↓
Clip + reproject to folha grid
  ↓
Gram-Schmidt fusion (ASTER + S2)
  ↓
Super-cube (stacked multi-band raster)
  ↓
Label raster (lithology rasterized to grid)
  ↓
Dataset extraction (pixel or patch)
  ↓
CNN training (PyTorch) → probability maps
```

### Territorial MCDA Flow (Layer 5)

```
Embedded GPKG (mc_100k, litologia_100k, ocorr_min_cprm)
  ↓
Grid construction (folha-based cells)
  ↓
Lithology scoring (per-cell SOM-derived scores)
  + Occurrence distance (distance to mineral occurrences)
  ↓
Restriction mask (conservation units, indigenous lands)
  + Slope constraint (DEM-derived)
  ↓
Priority classification (4 classes)
  ↓
Output rasters (PT_POTENCIAL, PT_RESTRICOES, PT_PRIORIDADE) + JSON report
```

### Adaptive Loop Flow (Layer 4, scaffold)

```
New observation (PostGIS insert)
  ↓
Trigger detection (planned: LISTEN/NOTIFY or polling)
  ↓
Per-folha data assembly
  ↓
Retrain classifier
  ↓
Generate new probability maps
  ↓
Compare vs previous run (delta rasters + metrics)
  ↓
Store outputs + metadata
```

---

## Plugin Architecture

Both QGIS plugins follow the standard pattern:

- **Entry point:** `classFactory(iface)` in `__init__.py` returns the plugin instance
- **Plugin class:** Manages toolbar actions, calls `initGui()` / `unload()`
- **UI:** `QDockWidget`-based dock panels
- **Differences:**
  - `preditor_terra`: Requires PostGIS connectivity, SOM workflows, scene preview
  - `preditor_territorial_mvp`: Self-contained with embedded GPKG, uses `QgsTask` for async processing

---

## Code Organization

| Directory | Era | Runtime | Description |
|-----------|-----|---------|-------------|
| `codes/` | 1→7 | System Python / QGIS Python | Core scripts and pipelines |
| `adaptive/` | 6 | System Python (CLI) | Adaptive loop package |
| `plugins/preditor_terra/` | 3 | QGIS Python | SOM/PostGIS plugin |
| `plugins/preditor_territorial_mvp/` | 7 | QGIS Python | Standalone MCDA plugin |
| `fonte/mapgeo/` | 2-3 | QGIS Python | Legacy plugin (deprecated) |
| `scripts/` | 7 | bash | Operational tooling |
| `tests/` | 7 | System Python (pytest) | Test suite |
| `sql/` | 6 | PostgreSQL | Schema definitions |
| `jupyternotebooks/` | 1-5 | Jupyter | Exploration (unmaintained) |
