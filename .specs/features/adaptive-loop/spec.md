# Adaptive Ingestion-Train-Predict Loop Specification

## Problem Statement

We want a shared PostgreSQL/PostGIS database where contributors can insert geological observations (points/lines/polygons) and acquisition datasets (aerogeophysics, satellite scenes via STAC). The system must periodically (or on-demand) read new data, merge it with existing curated data, retrain/update a lithology classifier, generate lithology class probability maps, and store the new outputs back into the database while comparing against previous outputs.

## Goals

- [ ] Provide a folha-driven pipeline that can be executed as a CLI job and is fully reproducible.
- [ ] Detect and ingest new/updated contributions and acquisitions from PostGIS and include them in dataset assembly.
- [ ] Train a baseline model that outputs per-class probabilities and generate per-folha probability rasters.
- [ ] Persist run lineage: inputs snapshot, feature set, model params, metrics, and output artifacts.
- [ ] Compare a new run with the previous run for the same folha and store a delta summary.

## Out of Scope

- Building a public web service with authentication/authorization.
- Real-time streaming ingestion.
- Distributed training infrastructure.
- GAN workflows (keep extension points, but not MVP).

---

## User Stories

### P1: Run a folha update job (MVP) ⭐

**User Story:** As a model operator, I want to run the pipeline for a given `folha` + `data_ref` so that I can generate updated lithology probability maps and store results with versioning.

**Acceptance Criteria:**
1. WHEN I run `pipeline run --folha SB21_ZA_II2_NE --data-ref 2008-06-01` THEN the system SHALL create a new `run` record with status `running` and a deterministic config snapshot.
2. WHEN the run completes successfully THEN the system SHALL store output artifacts (predicted class raster + probability rasters) and update the run status to `succeeded`.
3. WHEN a previous successful run exists for the same folha THEN the system SHALL compute and store a comparison summary (metrics delta and/or change stats).
4. WHEN required inputs are missing (no folha geometry, no training labels, no valid imagery) THEN the system SHALL mark the run as `failed` with an actionable error message.

**Independent Test:** Insert a minimal synthetic dataset for one folha and verify a run record + artifacts + metrics exist in Postgres after executing the CLI.

---

### P1: Ingest new contributions from PostGIS ⭐

**User Story:** As a contributor, I want to add rock/lithology observations (with attributes and provenance) so that the system can use them as training/evaluation signals.

**Acceptance Criteria:**
1. WHEN a new observation geometry is inserted/updated THEN the system SHALL detect it as part of the next dataset snapshot.
2. WHEN an observation has invalid geometry or missing required attributes THEN the system SHALL exclude it and record validation errors.
3. WHEN multiple observations conflict (same location, different lithology) THEN the system SHALL apply deterministic resolution rules (e.g., priority by source/revision/confidence) and record the decision.

**Independent Test:** Add 3 observations (1 invalid, 2 conflicting) and verify ingestion counts + validation logs + resolved training set.

---

### P2: Choose model backend at runtime

**User Story:** As a researcher, I want to select among RF/SVM/CNN/SOM (as available) via configuration so that I can compare approaches.

**Acceptance Criteria:**
1. WHEN I set `model.backend=rf` THEN the system SHALL train and predict using the RF implementation.
2. WHEN a backend is requested but dependencies are missing THEN the system SHALL fail fast with a clear installation hint.

---

### P3: Automated triggering

**User Story:** As a maintainer, I want the system to automatically enqueue runs when new data arrives so that maps stay updated.

**Acceptance Criteria:**
1. WHEN new data is inserted into tracked tables THEN the system SHALL create a pending job (via polling or LISTEN/NOTIFY).

---

## Edge Cases

- WHEN there are no new inputs since the last run THEN the system SHALL skip retraining (or mark as no-op) and avoid creating duplicate artifacts.
- WHEN STAC catalogs are unreachable THEN the system SHALL either use cached artifacts or fail with a retriable error.
- WHEN a folha is only partially covered by imagery THEN the system SHALL either reject the scene (MVP strict) or produce a degraded output with explicit quality flags.
- WHEN class set changes (new lithology labels) THEN the system SHALL version the label taxonomy and prevent mixing incompatible runs.

## Success Criteria

- [ ] A new contributor can run one folha end-to-end using only documented config and a PostGIS database.
- [ ] Every output map is traceable to a specific dataset snapshot + model params.
- [ ] Run-to-run comparison is stored and queryable per folha.
