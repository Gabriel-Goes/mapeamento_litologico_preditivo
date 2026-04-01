# External Integrations

## PostgreSQL / PostGIS

**Timeline:** [Era 3] initial connection → [Era 5] `config.py` centralization → [Era 6] `adaptive/settings.py` + SSH tunnel

- **Purpose:** Geometry boundaries (`carto.folhas_cartograficas`) and lithology polygons (`litologia.litologia_100k`) are the ground truth for every predictive map. The adaptive loop schema (`sql/adaptive_schema.sql`) tracks observations and ML runs.
- **Implementation surfaces:**
  - `codes/db_conn.py` [Era 3]: SQLAlchemy `Engine` via `get_engine`, exposes `get_folha_geom_geojson` and `get_litologia_100k_for_folha`.
  - `codes/config.py` [Era 5]: Centralized `PG_USER`, `PG_PASS`, `PG_HOST` env vars.
  - `adaptive/db.py` [Era 6]: Dual-mode engine — tries SQLAlchemy, falls back to psycopg2.
  - `adaptive/settings.py` [Era 6]: `@dataclass` Settings with `db_url` from env vars.
  - `fonte/mapgeo/` [Era 2-3]: Legacy hardcoded `geodatabase@localhost` (deprecated).
- **Configuration:** Connection strings from environment variables; SSH tunnel on port 62222 for remote access.

## SSH Tunnel

**Timeline:** [Era 6] Introduced for remote PostGIS access.

- **Purpose:** Secure PostgreSQL access from local QGIS to remote GeoServer without exposing the database port publicly.
- **Contract:** `QGIS client → SSH tunnel on port 62222 → PostgreSQL/PostGIS on 127.0.0.1:5432`.
- **Client-side:** Forwarded to `127.0.0.1:55432` on the local machine.
- **Documentation:** `docs/operacao/qgis_postgis_ssh_tunnel.md`.
- **QGIS export:** `geodb_conn.xml` with connection targeting the tunnel endpoint.

## STAC Catalogs

**Timeline:** [Era 5] Planetary Computer + BDC.

### Microsoft Planetary Computer
- **Purpose:** Acquire ASTER L1T and Sentinel-2 L2A imagery covering the target folha.
- **Implementation:** `codes/stac_utils.py` opens STAC clients with `pystac_client` and `planetary_computer.sign_inplace`. `codes/search_pair.py` orchestrates ASTER/Sentinel-2 queries.
- **Authentication:** `planetary_computer` signs requests automatically; assets cached locally via `raster_utils.download_pc_asset_to_local`.

### Brazil Data Cube (BDC)
- **Purpose:** Alternative STAC catalog for Landsat/CBERS imagery.
- **Implementation:** `codes/bdc_qgis_search.py` provides BDC-specific STAC search integrated with the QGIS dock.
- **Thumbnails:** `satellite_bdc/` stores downloaded Landsat thumbnails from BDC.

## QGIS / PyQt

**Timeline:** [Era 2] first interface → [Era 3] `fonte/mapgeo` plugin → [Era 5] consolidated dock → [Era 7] MCDA plugin

- **Purpose:** Provide in-software UI for previewing datasets, executing SOM/SVM/MCDA workflows, and inspecting metadata.
- **Plugins:**
  - `plugins/preditor_terra/` [Era 3]: SOM/PostGIS-backed, requires DB connectivity. Entry: `preditor_terra_plugin.py`.
  - `plugins/preditor_territorial_mvp/` [Era 7]: Standalone MCDA with embedded GPKG. Entry: `plugin.py`. Uses `QgsTask` for async processing.
  - `fonte/mapgeo/` [Era 2-3]: Legacy plugin (deprecated, partially broken imports).
- **Consolidated dock:** `codes/PreditoTerra_QGIS.py` [Era 5→7] — 3106-line monolithic dock widget with SOM, BDC, preview, and DB integration.
- **Execution:** Scripts run inside the QGIS Python console (`iface` imported from `qgis.utils`).

## GeoPackage

**Timeline:** [Era 7] Introduced for standalone MCDA plugin.

- **Purpose:** Self-contained spatial data storage that eliminates the need for PostGIS connectivity in field deployments.
- **Implementation:** `preditor_territorial_mvp/data/gamba_mvp.gpkg` bundles `mc_100k`, `litologia_100k`, and `ocorr_min_cprm` layers.
- **Build:** `scripts/build_gamba_mvp_data.sh` extracts data from PostGIS using `ogr2ogr`.
- **Access:** The MCDA plugin reads layers directly from the embedded GPKG.

## Raster Storage / Caching

- **Purpose:** Super-cube outputs, fused rasters, and cached STAC assets are written to disk for repeated analysis.
- **Implementation:** `ORBITAL_DIR` (from `codes/config.py`) stores `*.tif` and `.meta.json` artifacts.
- **Caching:** `raster_utils.download_pc_asset_to_local` persists downloaded STAC assets under `PC_CACHE_DIR`.

## Logging

**Timeline:** [Era 5] `log_utils.py` → [Era 7] `QgsMessageLog` in plugins

- **Implementation surfaces:**
  - `codes/log_utils.py` [Era 5]: File-based logging to `logs/preditor_terra*.log`.
  - `QgsMessageLog` [Era 7]: QGIS-native logging in `preditor_territorial_mvp`.
  - `print()` [Era 1-3]: Console output in legacy scripts.
  - `dock._log()` [Era 5→7]: Plugin dock logging in `PreditoTerra_QGIS.py`.
- **No remote logging services** are in use.
