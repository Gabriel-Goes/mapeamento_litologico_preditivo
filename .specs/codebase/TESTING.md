# Testing Infrastructure

## Evolution of Testing

### Era 1-3: No tests, ad-hoc validation via notebooks
- Validation was entirely manual: run a script, inspect the output, check notebook cells.
- SOM clustering results were visually inspected in QGIS.
- No test files, no assertions, no automated validation.

### Era 4: First test stubs (Jul 2025)
- PR #14 introduced initial test stubs:
  - `tests/test_database.py` — basic DB connectivity checks
  - `fonte/mapgeo/test/` — plugin UI test stubs
- These were scaffolding, not comprehensive tests. Most remained incomplete.

### Era 5: Manual validation via ML metrics (Nov 2025)
- `codes/train.py` outputs confusion matrices and classification reports (`sklearn.metrics`) during training.
- `codes/full_pipeline.py` includes `summarize_imagery_quality` for nodata/cloud fraction checks.
- Validation was still manual — run the pipeline, inspect the metrics, examine output rasters.
- No automated test execution.

### Era 7: pytest infrastructure (Mar 2026)
- First formal test suite with real assertions and synthetic fixtures.
- Tests validate MCDA logic without requiring real geospatial data or database access.

---

## Current Test Suite

### Test Frameworks
- **pytest** — primary test runner
- No CI integration — tests run manually via `pytest` from the repo root.

### Test Files

| File | Purpose | Fixtures |
|------|---------|----------|
| `tests/test_territorial_priority.py` | MCDA cluster scoring, priority classification | Synthetic geometries, mock folha grids |
| `tests/test_mvp_mcda_engine.py` | MCDA engine validation | Synthetic GPKG layers, in-memory geometries |

### Testing Patterns
- **Synthetic geometry fixtures:** Tests create in-memory geometries (points, polygons, grids) rather than loading real GPKG/PostGIS data.
- **No external dependencies:** Tests don't require PostGIS, STAC access, or real raster data.
- **Assertion-based:** Standard pytest assertions on computed scores, priority classes, and output shapes.

### Test Execution
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_territorial_priority.py

# Run with verbose output
pytest -v
```

### Coverage
- **Covered:** Territorial MCDA scoring logic (Era 7)
- **Not covered:** STAC search, raster fusion, CNN training, DB connectivity, QGIS plugin UI, adaptive loop
- **No coverage tool** configured.

---

## What Remains Untested

| Area | Era | Current Validation | Gap |
|------|-----|--------------------|-----|
| STAC search + ranking | 5 | Manual pipeline runs | No mocked STAC tests |
| Gram-Schmidt fusion | 5 | Visual raster inspection | No numerical tests |
| Super-cube construction | 5 | Manual pipeline runs | No shape/band tests |
| CNN training | 5 | Confusion matrices in console | No regression tests |
| PostGIS connectivity | 3-6 | `adaptive.cli doctor` | No integration tests |
| QGIS plugin UI | 3-7 | Manual QGIS testing | No headless UI tests |
| Adaptive loop | 6 | Not yet implemented | Stub only |
