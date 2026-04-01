# Project Structure

**Root:** `PreditorTerra-terraX`

## Directory Tree (annotated by era)

```
PreditorTerra-terraX/
├── codes/                          # [Era 1→7] Core pipelines, evolving since day one
│   ├── full_pipeline.py                  # [Era 5] End-to-end STAC→fusion→ML
│   ├── gs_fusion.py                      # [Era 5] Gram-Schmidt fusion
│   ├── supercube.py                      # [Era 5] Raster stacking
│   ├── search_pair.py                    # [Era 5] STAC scene ranking
│   ├── stac_utils.py                     # [Era 5] STAC client utilities
│   ├── raster_utils.py                   # [Era 5] Clipping, nodata, cloud metrics
│   ├── dataset_pixels.py                 # [Era 5] Pixel-level dataset extraction
│   ├── dataset_patches.py               # [Era 5] Patch-level dataset extraction
│   ├── train.py                          # [Era 5] PyTorch CNN training
│   ├── models_cnn.py                     # [Era 5] CNN architectures
│   ├── torch_datasets.py                 # [Era 5] PyTorch DataLoader wrappers
│   ├── aster_pipeline.py                 # [Era 5] ASTER scene ranking CLI
│   ├── gs_pipeline.py                    # [Era 5] Gram-Schmidt CLI
│   ├── db_conn.py                        # [Era 3] PostGIS connection helpers
│   ├── config.py                         # [Era 5] Centralized configuration
│   ├── labeling_lito.py                  # [Era 5] Lithology label rasterization
│   ├── PreditoTerra_QGIS.py             # [Era 5→7] Consolidated QGIS dock (3106 lines)
│   ├── PreditorTerra_Final.py            # [Era 3] Legacy QGIS dock (broken imports)
│   ├── bdc_qgis_search.py               # [Era 5] BDC STAC search
│   ├── territorial_priority.py           # [Era 7] MCDA cluster scoring
│   ├── territorial_sources.py            # [Era 7] Geospatial masking
│   ├── log_utils.py                      # [Era 5] File logging
│   ├── scene_preview.py                  # [Era 5] Scene preview generation
│   ├── preditor_terra.py                 # [Era 3] Early QGIS integration
│   ├── PreditorTerra_qgis.py            # [Era 3] Alternate QGIS entry point
│   ├── PreditorTerraQGIS.py             # [Era 3] Alternate QGIS entry point
│   ├── TerraX.py                         # [Era 5] QGIS variant
│   ├── geof_interp_widget.py            # [Era 1] Geophysical interpolation widget
│   └── ...                               # [Era 1-5] Additional scripts, notebooks, tests
├── adaptive/                       # [Era 6] Adaptive loop package
│   ├── __init__.py
│   ├── cli.py                            # doctor, init-db, run commands
│   ├── db.py                             # Dual-mode engine (SQLAlchemy/psycopg2)
│   ├── settings.py                       # @dataclass Settings from env vars
│   └── pipeline/
│       └── run.py                        # Stub orchestrator
├── plugins/                        # [Era 3→7] QGIS plugins
│   ├── preditor_terra/                   # [Era 3] SOM/PostGIS-backed plugin
│   │   ├── __init__.py
│   │   ├── preditor_terra_plugin.py
│   │   ├── metadata.txt
│   │   └── icon.png
│   └── preditor_territorial_mvp/         # [Era 7] Standalone MCDA plugin
│       ├── __init__.py
│       ├── plugin.py                     # classFactory entry point
│       ├── dock.py                       # QDockWidget UI
│       ├── mcda_engine.py                # MCDA scoring engine
│       ├── metadata.txt
│       ├── icon.png
│       ├── data/                         # Embedded GPKG data
│       └── README_INSTALL.txt
├── scripts/                        # [Era 7] Operational tooling
│   ├── build_gamba_mvp_data.sh           # GPKG assembly from PostGIS
│   ├── build_qgis_plugin_mvp_zip.sh     # ZIP packaging
│   ├── prepare_gamba_mvp_delivery.sh     # Full delivery workflow
│   ├── collect_demo_evidence.sh          # Demo screenshot collection
│   ├── run_qgis_preditor.sh              # QGIS launcher with env
│   ├── run_qgis_preditor_remote.sh       # QGIS launcher (remote DB)
│   ├── run_qgis_preditor_demo.sh         # Demo launcher
│   ├── run_qgis_debug_cycle.sh           # Debug iteration script
│   ├── check_qgis_remote_env.sh          # Remote environment check
│   ├── install_qgis_plugin_dev.sh        # Dev plugin install
│   ├── triage_preditor_logs.py           # Log analysis utility
│   ├── preditor_qgis.env.example         # Env template
│   ├── preditor_qgis.remote.env          # Remote env config
│   └── preditor_qgis.remote.env.example  # Remote env template
├── tests/                          # [Era 7] pytest suite
│   ├── test_territorial_priority.py      # MCDA scoring tests
│   └── test_mvp_mcda_engine.py           # MCDA engine tests
├── sql/                            # [Era 6] Schema definitions
│   └── adaptive_schema.sql               # PostGIS schema for adaptive loop
├── fonte/mapgeo/                   # [Era 2-3] Legacy QGIS plugin (deprecated)
│   ├── mapgeo.py                         # Main plugin logic
│   ├── mapgeo_dialog.py                  # Dialog UI
│   ├── mapgeo_dialog_base.ui             # Qt Designer UI
│   ├── nucleo/                           # Core modules
│   ├── fonte/                            # Data sources
│   ├── test/                             # Legacy test stubs
│   └── ...                               # Build/i18n infrastructure
├── satellite_bdc/                  # [Era 5] BDC Landsat thumbnails
├── dist/                           # [Era 7] Built ZIP artifacts
├── docs/                           # [Era 1→7] Research documents
│   ├── uml/                              # UML diagrams
│   ├── posters/                          # Academic posters
│   ├── relatorios/                       # Reports (SIICUSP, TrabalhoFinal)
│   ├── gamba/                            # Gamba fieldwork docs
│   ├── operacao/                         # Operational guides
│   └── conversas/                        # Development discussion logs
├── jupyternotebooks/               # [Era 1-5] Exploration sandboxes
├── candidatos_orbitais/            # [Era 5] STAC experiments
├── dotfiles/                       # [Era 1] Environment manifests
├── logs/                           # [Era 5] Runtime logs
├── .specs/                         # [Era 6] Formal specifications
│   ├── project/                          # PROJECT, ROADMAP, STATE
│   ├── codebase/                         # ARCHITECTURE, STRUCTURE, STACK, etc.
│   └── features/                         # Feature specs (adaptive-loop)
├── CODEX.md                        # [Era 5] Pipeline design document
├── AGENTS.md                       # [Era 5] Agent configuration (legacy)
├── README.md                       # [Era 1→7] Main documentation
└── geodb_conn.xml                  # [Era 6] QGIS PostgreSQL connection export
```

## Module Organization

### `codes/` — Core Pipelines
- **Purpose:** Main implementation of STAC search, raster handling, dataset prep, ML training, QGIS dock integration, and territorial scoring.
- **Era span:** Contains code from every era. Earliest files are geophysical processing (Era 1); most recent are territorial MCDA (Era 7).
- **Subdomains:**
  - `search_pair`/`stac_utils` — STAC catalog searches [Era 5]
  - `gs_fusion`/`supercube` — raster fusion [Era 5]
  - `dataset_*`/`labeling_lito` — ML dataset preparation [Era 5]
  - `train`/`models_cnn`/`torch_datasets` — PyTorch training [Era 5]
  - `territorial_*` — MCDA scoring [Era 7]
  - `PreditoTerra_QGIS.py` — consolidated QGIS dock [Era 5→7]

### `adaptive/` — Adaptive Loop Package
- **Purpose:** Formal package for the data-driven re-prediction loop.
- **Key modules:** CLI (`doctor`, `init-db`, `run`), dual-mode DB engine, env-based settings.
- **Era:** 6 (Jan–Feb 2026)

### `plugins/` — QGIS Plugins
- **Purpose:** Installable QGIS plugins.
- `preditor_terra/` [Era 3]: SOM/PostGIS-backed, requires DB connectivity.
- `preditor_territorial_mvp/` [Era 7]: Standalone MCDA with embedded GPKG, no external DB needed.

### `scripts/` — Operational Tooling
- **Purpose:** Shell scripts for QGIS launching, plugin building, data preparation, and demo workflows.
- **Era:** Primarily Era 7.

### `tests/` — Test Suite
- **Purpose:** pytest tests with synthetic geometry fixtures.
- **Era:** 7 (first formal test infrastructure).

### Legacy Directories
- `fonte/mapgeo/` [Era 2-3]: Original QGIS plugin, deprecated but still present.
- `jupyternotebooks/` [Era 1-5]: Exploration notebooks, not maintained.
- `candidatos_orbitais/` [Era 5]: STAC experiments.
- `dotfiles/` [Era 1]: Environment manifests (conda/pip).
