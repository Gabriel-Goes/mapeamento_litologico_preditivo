# Project Structure

**Root:** `/home/ggrl/projetos/PreditorTerra`

## Directory Tree (≤3 levels)
```
PreditorTerra/
├── AGENTS.md
├── README.md
├── install.sh
├── app                # wrapper CI/launcher script
├── dotfiles/          # conda/pip environment manifests
├── codes/             # core pipelines, datasets, UI scripts
│   ├── full_pipeline.py
│   ├── gs_fusion.py
│   ├── supercube.py
│   ├── dataset_pixels.py
│   ├── dataset_patches.py
│   ├── train.py
│   ├── models_cnn.py
│   ├── preditor_terra.py
│   └── ...
├── docs/
│   ├── uml/
│   ├── posters/
│   └── relatorios/
├── jupyternotebooks/  # notebooks mixing STAC + ML experiments
├── candidatos_orbitais/ # additional STAC experiments
├── sources/           # legacy scripts/tutorials
└── logs/
    └── preditor_terra*.log
```

## Module Organization
### `codes/`
- **Purpose:** Main implementation of STAC search, raster handling, dataset prep, and ML training/UI drivers.
- **Key files:** `aster_pipeline.py`, `full_pipeline.py`, `gs_pipeline.py`, `PreditorTerra_Final.py`, `train.py`, `models_cnn.py`, `torch_datasets.py`.
- **Subdomains:** `search_pair`/`stac_utils` handle catalog searches; `gs_fusion`/`supercube` perform raster fusion; `dataset_*` and `labeling_lito` prepare ML inputs.

### `dotfiles/`
- **Purpose:** Defines reproducible environments (again, `environment.yml` plus a secondary `requirements.txt`).
- **Key artifacts:** `environment.yml` (conda env with geopandas, verde, scikit-learn, torch, qgis) and instructions inside `requirements.txt`.

### `docs/`
- **Purpose:** Documentation, research posters, UML diagrams, and abstract project planning stored in subdirectories (`uml/`, `posters/`, `projetos/`).

### `jupyternotebooks/` & `candidatos_orbitais/`
- **Purpose:** Exploratory notebooks walkthroughs for STAC discovery, labeling, and ML training. Typically contain repeated logic for STAC queries, dataset assembly, and digital mapping.

### `sources/`
- **Purpose:** Legacy or auxiliary scripts (`scripts/`, `tutoriais/`) referenced by notebooks or older pipelines.

### `logs/`
- **Purpose:** Runtime logs created by `codes/log_utils.py` and the PyQt interface.

### `app` + `install.sh`
- `app` is an executable BP `/bin/bash` wrapper; `install.sh` bootstraps the Python environment (virtualenv/conda). Both live at the repository root.
