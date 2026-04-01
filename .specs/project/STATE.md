# State

**Last Updated:** 2026-03-18T00:00:00-03:00
**Current Work:** Evolutionary documentation rewrite; M0.1 (Territorial MCDA MVP) delivered

---

## Recent Decisions (Last 60 days)

### AD-001: Unit of work is folha-driven (2026-02-14)

**Decision:** The primary pipeline execution unit is `(folha, data_ref)`.
**Reason:** Matches existing repo logic (folhas cartograficas, STAC queries, per-folha clipping) and simplifies versioning and comparisons.
**Trade-off:** Cross-folha/global models become a later concern.
**Impact:** DB schema, outputs, and runs are keyed by `folha`.

### AD-002: Store large raster outputs as files + DB pointers (v1) (2026-02-14)

**Decision:** Persist probability rasters as GeoTIFF artifacts on disk/object storage and store metadata + paths/URIs in PostGIS.
**Reason:** PostGIS raster storage can bloat DB and complicate backup/IO; artifact pointers are simpler for MVP.
**Trade-off:** Requires shared filesystem or object store conventions.
**Impact:** Output tables will include `artifact_uri`, checksums, and footprint metadata.

### AD-003: External QGIS access uses SSH tunnel, not direct Postgres exposure (2026-03-12)

**Decision:** The canonical access path for a user opening the Preditor Terra database in a local QGIS is `QGIS client -> SSH tunnel on port 62222 -> PostgreSQL/PostGIS on 127.0.0.1:5432` on the GeoServer.
**Reason:** The GeoServer is a personal service outside the IPT network, the available remote access path is SSH on port `62222`, and this avoids exposing PostgreSQL directly on the public network.
**Trade-off:** The user must keep the SSH tunnel open before launching the QGIS connection.
**Impact:** Docs, sample QGIS connection exports, and operational guidance should target `127.0.0.1:55432` on the client side while keeping PostgreSQL local to the server.

### AD-004: Embedded GPKG for standalone MCDA plugin (2026-03-14)

**Decision:** The territorial MVP plugin bundles its own GeoPackage (`gamba_mvp.gpkg`) instead of requiring PostGIS connectivity.
**Reason:** Field deployment with Gamba requires a plugin that works offline, without SSH tunnels or database servers. GPKG provides self-contained spatial data storage.
**Trade-off:** Data must be re-extracted from PostGIS when the source data changes; no live sync.
**Impact:** Plugin is fully self-contained. Build script `scripts/build_gamba_mvp_data.sh` extracts from PostGIS using `ogr2ogr`.

### AD-005: QgsTask for responsive MCDA processing (2026-03-15)

**Decision:** Long-running MCDA operations run as `QgsTask` background tasks instead of blocking the QGIS main thread.
**Reason:** MCDA grid scoring on large folhas can take tens of seconds; blocking the UI makes QGIS appear frozen.
**Trade-off:** Adds complexity to error handling and progress reporting.
**Impact:** Users can continue working in QGIS during MCDA processing; cancel is supported.

---

## Active Blockers

### B-001: Environment/install manifests are inconsistent

**Discovered:** 2026-02-14
**Impact:** New contributors may fail to reproduce the environment (e.g., `dotfiles/requirements.txt` is not a valid pip requirements file; `install.sh` installs via pip).
**Workaround:** Use `dotfiles/environment.yml` as the primary spec, then add missing pip deps manually.
**Resolution:** Replace with a single source of truth (either conda env + pip section, or `pyproject.toml`), and fix `install.sh`.

### B-002: Some QGIS entrypoints reference missing modules

**Discovered:** 2026-02-14
**Impact:** `codes/PreditorTerra_Final.py` imports `src` which is not present; this breaks QGIS execution paths.
**Workaround:** Use `PreditoTerra_QGIS.py` (Era 5→7) as the active QGIS dock; use `preditor_territorial_mvp` plugin for MCDA.
**Resolution:** Either add missing modules, or deprecate/archive those scripts.

### B-003: End-to-end PostGIS access still needs runtime validation with the SSH-tunnel contract

**Discovered:** 2026-03-12
**Impact:** The PostgreSQL service was manually confirmed active on the GeoServer host after restart, but the repo still lacks a completed runtime validation for the full client contract: local listener on the server, required schemas/tables, authenticated role, and QGIS access through the SSH tunnel.
**Workaround:** Validate the server locally with `pg_isready`/`psql`, then validate the client path using the SSH tunnel on `62222` and the forwarded local port `55432`.
**Resolution:** Complete the operational checklist from `docs/operacao/qgis_postgis_ssh_tunnel.md` and only then downgrade this blocker.

### B-004: DB/QGIS integration paths diverged in config and dependencies

**Discovered:** 2026-03-12
**Impact:** The repo still mixes multiple DB contracts and runtime assumptions: `codes/config.py` defaults to `geologia@localhost`, QGIS launch scripts default to `geologia@127.0.0.1:5432` on the server, the exported QGIS connection now targets `127.0.0.1:55432` on the client via SSH tunnel, and the legacy `fonte/mapgeo` stack hardcodes `geodatabase@localhost`. In addition, `adaptive/*` can fall back to `psycopg2`, but `codes/db_conn.py` hard-requires `sqlalchemy` and currently fails to import; the current Python also lacks `rasterio`, `rioxarray`, `pystac_client`, `planetary_computer`, and `geoalchemy2`, leaving several PostGIS/QGIS/STAC paths only partially operable.
**Workaround:** Treat `adaptive/*` as the only DB connectivity path that degrades gracefully in this environment, and treat `fonte/mapgeo` plus `codes/db_conn.py` as non-authoritative until connection settings and dependencies are aligned.
**Resolution:** Consolidate on one database name/host/env-var contract, remove or quarantine legacy hardcoded DSNs, and make dependency expectations explicit per runtime surface (system Python, QGIS Python, CLI).

---

## Lessons Learned

### L-001: Centralized config is mandatory for pipeline stability

**Context:** Multiple modules import constants like `ORBITAL_DIR`, `PC_STAC_URL`, and STAC catalog config.
**Problem:** Missing/fragmented config breaks imports and makes the pipeline non-runnable.
**Solution:** Consolidate DB/STAC/output settings in `codes/config.py` with env-var overrides.
**Prevents:** Silent divergence between README, notebooks, and runtime behavior.

### L-002: "Configured" and "operational" are different states for PostGIS/QGIS

**Context:** The brownfield review found several files that declare PostgreSQL/PostGIS settings, but runtime checks did not confirm a working local database or a consistent dependency set.
**Problem:** Static config alone gave a false impression that the DB-backed flows were ready, while the actual environment failed on reachability and imports.
**Solution:** Validate operational status with runtime evidence (`adaptive.cli doctor`, `pg_isready`, targeted import checks) before treating a DB/QGIS path as usable.
**Prevents:** Spending time debugging higher-level STAC/QGIS logic when the base PostgreSQL/PostGIS contract is not yet live.

### L-003: Standalone GPKG eliminates deployment friction

**Context:** The territorial MVP needed to work for Gamba fieldwork without requiring PostGIS or SSH tunnels.
**Problem:** PostGIS dependency made field deployment impractical — no guarantee of network access or database availability.
**Solution:** Embed a GeoPackage within the plugin ZIP. Build from PostGIS using `ogr2ogr`, but deploy as self-contained GPKG.
**Prevents:** Plugin failures due to missing DB connectivity in the field.

### L-004: QgsTask is essential for responsive QGIS plugins

**Context:** MCDA grid scoring on large folhas blocks the QGIS main thread for tens of seconds.
**Problem:** QGIS appears frozen during processing; users may force-quit.
**Solution:** Subclass `QgsTask` for all long-running operations; report progress via `setProgress()`.
**Prevents:** Poor user experience and potential data loss from force-quitting QGIS.

---

## Preferences

**Model Guidance Shown:** never
