# Architecture

**Pattern:** Modular monolith with pipelines organized as standalone scripts under `codes/` and exploratory notebooks under `jupyternotebooks/` + `candidatos_orbitais/`.

## High-Level Structure
- Input: PostgreSQL/PostGIS (`db_conn.get_folha_geom_geojson`, `labeling_lito.get_litologia_100k_for_folha`) supplies folha boxes and lithology polygons for each request.
- Enrichment: `codes/search_pair` + `codes/stac_utils` query prioritized STAC catalogs (Planetary Computer, others configured via `DEFAULT_STAC_CATALOGS`) to find ASTER and Sentinel-2 scenes that fully cover the folha.
- Preprocessing: `codes/raster_utils` clips rasters, measures nodata/cloud fractions, and `codes/gs_fusion` fuses ASTER VNIR/SWIR with Sentinel-2 PAN through Gram-Schmidt, producing inputs for `codes/supercube`.
- Labeling: `codes/labeling_lito.build_label_raster_for_folha` rasterizes PostGIS lithology and aligns it with the super-cube raster grid.
- Dataset creation: `codes/dataset_pixels.extract_pixel_dataset` (per-pixel spectral vectors) and `codes/dataset_patches.generate_patches` (patch-based labels) consume the super-cube + label raster to produce NumPy arrays for training.
- ML: `codes/torch_datasets` wraps those arrays for PyTorch; `codes/models_cnn` defines pixel/patch CNNs; `codes/train.train_pixel_cnn` and `train_pixel_cnn` orchestrate training/evaluation loops.
- Ops/UI: `codes/PreditorTerra_Final.py` and related QGIS scripts (`PreditorTerra_qgis.py`, `TerraX.py`, etc.) expose the workflow as a PyQt dock, providing UI widgets, preview generation, and logging (`logs/preditor_terra*.log`).
- Supporting flows: `codes/aster_pipeline.py` ranks ASTER scenes via `search_pair`; `codes/full_pipeline.py` orchestrates the end-to-end selection → fusion → dataset → preview steps; `codes/gs_pipeline.py` exposes the Gram-Schmidt process as a CLI.

## Data Flow Highlights
1. **Geometry + lithology retrieval:** `db_conn.get_folha_geom_geojson` and `labeling_lito` query PostGIS metadata (`carto.folhas_cartograficas`, `litologia.litologia_100k`) to get both the folha boundary and lithological polygons in the super-cube CRS.
2. **Scene selection:** `search_pair.search_aster_cloudfree_for_folha` runs STAC searches across prioritized catalogs (`codes/stac_utils.iter_catalog_clients`) applying coverage, cloud, and temporal filters; `search_s2_cloudfree_for_folha_given_aster` finds Sentinel-2 scenes aligned with the ASTER selection.
3. **Clipping & fusion:** `raster_utils.clip_raster_to_folha` trims the chosen assets; `gs_fusion.run_gs_pair_pipeline` downloads Sentinel-2 bands, reprojects ASTER data, fuses them, and stores outputs in `ORBITAL_DIR`.
4. **Super-cube & labels:** `supercube.build_supercube` stacks Sentinel-2 and fused ASTER bands, writing a GeoTIFF + metadata; `labeling_lito.build_label_raster_for_folha` rasterizes lithology to match the grid.
5. **Dataset extraction & ML:** Pixel/patch datasets are extracted, normalized, and fed into PyTorch training routines with progress logged to console (`train.py`).
6. **Inference/UI:** Trained models can be applied via `PreditorTerra_Final` in QGIS or via notebooks for manual inspection.

## Code Organization
- `codes/` holds executable scripts (`full_pipeline`, `gs_pipeline`, `aster_pipeline`, `PreditorTerra_*`, `train`, `models_cnn`, support modules). Files typically expose a `main()` or CLI entry guarded by `if __name__ == "__main__":`.
- `dotfiles/` contains environment manifests used to reproduce the Python ecosystem.
- `jupyternotebooks/` and `candidatos_orbitais/` are experimentation sandboxes: they mix data download, STAC exploration, and modeling prototypes.
- `docs/` stores research posters, UML diagrams, and text docs describing workflows (e.g., `docs/uml/`).
- `logs/` keeps historical log output that matches the console log pattern from `log_utils.log_stdout`.
- `sources/` (with `scripts/` and `tutoriais/`) hosts older tutorial artefacts referenced by notebooks.

## Example Components
- **STAC ranking:** `codes/aster_pipeline.py` filters for VNIR/SWIR assets (`item_has_assets`), sorts by coverage/cloud/delta-days, and optionally writes CSV/JSON.
- **Fusion & super-cube:** `codes/gs_fusion.py` + `codes/supercube.py` deliver Gram-Schmidt fusion outputs used by `codes/full_pipeline.py` and `gs_pipeline.py`.
- **ML training:** `codes/train.py` uses `PixelSpectralDataset` and `PatchDataset` defined in `torch_datasets.py` plus CNN definitions from `models_cnn.py`.
- **UI gadget:** `PreditorTerra_Final.py` integrates PyQt widgets, preview generation (`scene_preview`), and Sat/STAC metadata tracking (`sat_store`).
