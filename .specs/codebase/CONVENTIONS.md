# Code Conventions

## Naming
- **Files:** Lowercase with underscores, e.g., `gs_fusion.py`, `dataset_patches.py`, `torch_datasets.py`. Exceptions exist for QGIS entry points (`PreditorTerra_Final.py`, `PreditorTerra_qgis.py`) to match the GUI names.
- **Functions/methods:** Snake case (`filter_rankable_candidates`, `build_supercube`, `train_pixel_cnn`); the CLI entry points follow `main()` conventions with `if __name__ == "__main__": main()`.
- **Classes:** PascalCase (`PixelCNN`, `PatchCNN`).
- **Constants:** Uppercase with underscores (`DEFAULT_ASTER_TARGET_DATE`, `PREFERRED_ASSETS`, `ORBITAL_DIR`).
- **Variables:** Snake case with descriptive names (e.g., `folha_geom`, `s2_ref_da`, `label_raster`, `candidates_sorted`).

## Imports & Modules
- Standard library imports appear before third-party, then local modules, mirroring the isolation seen in `codes/full_pipeline.py` (`import argparse`, `import json`, third-party libs, followed by `from config import ORBITAL_DIR`).
- Local modules are imported by filename rather than package, reflecting the flat `codes/` namespace (e.g., `from dataset_pixels import extract_pixel_dataset`).
- `from __future__ import annotations` is used at the top of many files to keep type hints clean.

## Documentation & Comments
- Descriptive inline comments and block comments are in Portuguese and explain high-level intent (examples in `PreditorTerra_Final.py`).
- Only critical helpers expose docstrings (e.g., `dataset_patches.generate_patches` contains a docstring that explains inputs/outputs). Many files rely on contextual names rather than docstrings.

## Type Safety & Error Handling
- Typing hints appear selectively (function signatures, return types) but are not strictly enforced; many helper functions return `Any` or `dict` to keep scripts flexible.
- Errors are surfaced through exceptions (`raise RuntimeError`, `SystemExit`) with Portuguese messages (see `db_conn.get_folha_geom_geojson` or `full_pipeline.resolve_pair`).
- Logging is done via `print()` statements and helper `log_utils.log_stdout` rather than structured logging frameworks.

## Code Structure
- Scripts favor single-responsibility helpers, e.g., `raster_utils` exposes clipping, nodata counts, and cloud computations as separate functions.
- Each CLI script constructs an `argparse.ArgumentParser`, parses args, then calls `main()` (see `aster_pipeline.py`, `gs_pipeline.py`).
- Long-running operations are often wrapped with helper functions imported from other modules to keep entry scripts readable.
