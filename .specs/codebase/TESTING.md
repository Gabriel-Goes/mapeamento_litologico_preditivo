# Testing Infrastructure

## Test Frameworks
- **Unit/Integration/E2E:** Not present. The repo currently does not expose dedicated test suites or harnesses.
- **Coverage:** Not measured; experimentation is ad-hoc via notebooks or script runs.

## Test Organization
- **Location:** No `tests/` directory; validation happens inside the same scripts (`codes/train.py`, `codes/full_pipeline.py`) or within exploratory notebooks under `jupyternotebooks/` and `candidatos_orbitais/`.
- **Naming:** No test files to observe, so no naming conventions applied.

## Testing Patterns
- **Ad-hoc validation:** Scripts print accuracy/confusion matrices (`train.py` uses `confusion_matrix`, `classification_report`). Users manually inspect `logs/preditor_terra*.log` or notebook outputs.
- **Manual data checks:** `codes/full_pipeline.py` contains helper functions such as `summarize_imagery_quality` that compute nodata/cloud fractions for manual validation.

## Test Execution
- **Commands:** None documented; practitioners run `python train.py ...` or `python full_pipeline.py ...` directly. No `pytest`/`unittest` commands exist.
- **Configuration:** No special test configuration files or flags.
- **CI:** No continuous integration configuration detected in the repository.
