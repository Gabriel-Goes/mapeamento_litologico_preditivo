# Architectural Concerns

These concerns are framed by the era that introduced them and how they have accumulated over time. They are not bugs — they are structural tensions that arise from a brownfield project spanning 7 eras of development.

---

## C-001: Legacy accumulation

**Origin:** Era 1-3 code still present, partially broken.
**Manifestation:** `fonte/mapgeo/` is a complete but deprecated QGIS plugin. `codes/PreditorTerra_Final.py` imports a nonexistent `src` module. Multiple alternate QGIS entry points (`PreditorTerra_qgis.py`, `PreditorTerraQGIS.py`, `TerraX.py`, `TerraY.py`) coexist without clear lifecycle.
**Risk:** Contributors waste time navigating dead code; broken imports cause confusing errors.
**Mitigation path:** Quarantine or archive Era 1-3 artifacts that are no longer active.

---

## C-002: Multiple DB contracts

**Origin:** Each era added its own database connection pattern.
**Surfaces (4 today):**
1. `codes/db_conn.py` [Era 3] — SQLAlchemy `create_engine`, targets `geologia@localhost`
2. `codes/config.py` [Era 5] — env vars (`PG_USER`, `PG_PASS`, `PG_HOST`) with defaults
3. `adaptive/db.py` [Era 6] — dual-mode (SQLAlchemy → psycopg2 fallback), reads from `adaptive/settings.py`
4. `fonte/mapgeo/` [Era 2-3] — hardcoded `geodatabase@localhost`
**Risk:** Config drift — different modules connect to different databases or fail inconsistently.
**Mitigation path:** Consolidate on `adaptive/settings.py` as the canonical DB config; adapt or deprecate older surfaces.

---

## C-003: Monolithic growth

**Origin:** `codes/PreditoTerra_QGIS.py` grew across Era 5→7.
**Manifestation:** 3106 lines in a single file combining SOM workflows, BDC search, scene preview, DB integration, and dock widget management.
**Risk:** Difficult to test, review, or modify without unintended side effects.
**Mitigation path:** Extract cohesive subsystems (SOM, BDC, preview) into separate modules; keep the dock as a thin orchestrator.

---

## C-004: Dependency fragmentation

**Origin:** Three runtime surfaces evolved independently.
**Surfaces:**
1. **System Python** (CLI scripts, `adaptive/`): needs `psycopg2`, `sqlalchemy`, `geopandas`, etc.
2. **QGIS Python** (plugins, dock): needs `qgis.core`, `qgis.PyQt`, plus whatever `codes/` modules import.
3. **CLI/bash** (`scripts/`): needs `ogr2ogr`, `pg_isready`, standard Unix tools.
**Manifestation:** No unified dependency manifest. `dotfiles/environment.yml` is incomplete; `requirements.txt` is not a valid pip requirements file; `install.sh` may not reproduce the full environment.
**Risk:** New contributors cannot reliably set up the project.
**Mitigation path:** Create a single `pyproject.toml` or curated `environment.yml` per runtime surface.

---

## C-005: No CI/CD

**Origin:** Tests arrived in Era 7 but aren't automated.
**Manifestation:** `pytest` works locally but there's no GitHub Actions, pre-commit hooks, or automated quality gates.
**Risk:** Regressions go undetected until manual testing. Plugin ZIP builds are manual.
**Mitigation path:** Add a minimal GitHub Actions workflow: `pytest` + basic import checks.

---

## C-006: Fragile schema assumptions

**Origin:** Era 7 MCDA code discovers column names dynamically.
**Manifestation:** `territorial_priority.py` and `mcda_engine.py` introspect GPKG layer attributes at runtime rather than validating against a known schema.
**Risk:** Renamed or missing columns cause cryptic runtime errors instead of clear validation failures.
**Mitigation path:** Add schema validation at plugin load time — check expected columns exist before running MCDA.

---

## C-007: Hardcoded MCDA weights

**Origin:** Era 7 priority scoring.
**Manifestation:** Lithology scores and distance weights are hardcoded in `mcda_engine.py` and `territorial_priority.py`. Not configurable via the plugin UI or an external config file.
**Risk:** Different fieldwork contexts require different weight profiles; changes require code edits.
**Mitigation path:** Expose weights as configurable parameters (UI sliders or a JSON/YAML config).

---

## C-008: Mixed logging approaches

**Origin:** Each era added its own logging method.
**Approaches (4 today):**
1. `print()` [Era 1-3] — console output in legacy scripts
2. `log_utils.log_stdout` [Era 5] — file logging to `logs/preditor_terra*.log`
3. `QgsMessageLog` [Era 7] — QGIS-native logging in territorial MVP plugin
4. `dock._log()` [Era 5→7] — internal dock widget logging in `PreditoTerra_QGIS.py`
**Risk:** Debugging requires checking multiple outputs; no unified log stream.
**Mitigation path:** Standardize on Python `logging` module with handlers for file, console, and `QgsMessageLog` as appropriate per runtime surface.
