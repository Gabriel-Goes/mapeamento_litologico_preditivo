-- Adaptive Loop MVP schema
--
-- Notes:
-- - Uses separate schemas for clarity: contrib (inputs) and ml (runs/outputs).
-- - Keeps geometry in EPSG:4326 for interoperability; ingestion should transform.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS contrib;
CREATE SCHEMA IF NOT EXISTS ml;

-- -----------------------------------------------------------------------------
-- Collaborative inputs
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS contrib.observations (
    id           bigserial PRIMARY KEY,
    geom         geometry(Geometry, 4326) NOT NULL,
    folha_codigo text,
    label        text NOT NULL,
    confidence   double precision,
    source       text,
    attrs        jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_observations_geom ON contrib.observations USING gist (geom);
CREATE INDEX IF NOT EXISTS ix_observations_folha ON contrib.observations (folha_codigo);
CREATE INDEX IF NOT EXISTS ix_observations_updated_at ON contrib.observations (updated_at);

CREATE TABLE IF NOT EXISTS contrib.acquisitions (
    id           bigserial PRIMARY KEY,
    kind         text NOT NULL,
    geom         geometry(Geometry, 4326),
    time_start   timestamptz,
    time_end     timestamptz,
    attrs        jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_acquisitions_geom ON contrib.acquisitions USING gist (geom);
CREATE INDEX IF NOT EXISTS ix_acquisitions_kind ON contrib.acquisitions (kind);
CREATE INDEX IF NOT EXISTS ix_acquisitions_updated_at ON contrib.acquisitions (updated_at);

-- -----------------------------------------------------------------------------
-- Run tracking + artifacts
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ml.run (
    id            bigserial PRIMARY KEY,
    folha_codigo  text NOT NULL,
    data_ref      date,
    status        text NOT NULL,
    config_json   jsonb NOT NULL DEFAULT '{}'::jsonb,
    dataset_hash  text,
    model_backend text,
    model_params  jsonb NOT NULL DEFAULT '{}'::jsonb,
    started_at    timestamptz,
    finished_at   timestamptz,
    error_message text
);

CREATE INDEX IF NOT EXISTS ix_run_folha ON ml.run (folha_codigo);
CREATE INDEX IF NOT EXISTS ix_run_status ON ml.run (status);
CREATE INDEX IF NOT EXISTS ix_run_started_at ON ml.run (started_at);

CREATE TABLE IF NOT EXISTS ml.metric (
    id      bigserial PRIMARY KEY,
    run_id  bigint NOT NULL REFERENCES ml.run(id) ON DELETE CASCADE,
    name    text NOT NULL,
    value   double precision NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_metric_run_id ON ml.metric (run_id);

CREATE TABLE IF NOT EXISTS ml.artifact (
    id       bigserial PRIMARY KEY,
    run_id   bigint NOT NULL REFERENCES ml.run(id) ON DELETE CASCADE,
    kind     text NOT NULL,
    uri      text NOT NULL,
    checksum text,
    attrs    jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_artifact_run_id ON ml.artifact (run_id);
CREATE INDEX IF NOT EXISTS ix_artifact_kind ON ml.artifact (kind);

CREATE TABLE IF NOT EXISTS ml.run_compare (
    id          bigserial PRIMARY KEY,
    run_id_new  bigint NOT NULL REFERENCES ml.run(id) ON DELETE CASCADE,
    run_id_prev bigint NOT NULL REFERENCES ml.run(id) ON DELETE CASCADE,
    summary     jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_run_compare_new ON ml.run_compare (run_id_new);
