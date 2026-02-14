# State

**Last Updated:** 2026-02-14T07:18:39-03:00
**Current Work:** Adaptive Loop MVP - spec/design/tasks

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
**Workaround:** Focus MVP on CLI pipelines under `codes/` (STAC + fusion + datasets + ML).
**Resolution:** Either add missing modules, or deprecate/archival those scripts.

---

## Lessons Learned

### L-001: Centralized config is mandatory for pipeline stability

**Context:** Multiple modules import constants like `ORBITAL_DIR`, `PC_STAC_URL`, and STAC catalog config.
**Problem:** Missing/fragmented config breaks imports and makes the pipeline non-runnable.
**Solution:** Consolidate DB/STAC/output settings in `codes/config.py` with env-var overrides.
**Prevents:** Silent divergence between README, notebooks, and runtime behavior.

---

## Preferences

**Model Guidance Shown:** never
