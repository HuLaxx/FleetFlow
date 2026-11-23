-- Source-of-truth for dbt is the immutable local Parquet run, not a live GPS database.
-- Apply only to an isolated/dev PostgreSQL database after reviewed migration.
CREATE TABLE IF NOT EXISTS public.gps_hourly_curated (
    run_key TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    vehicle_id UUID NOT NULL,
    hour_utc TIMESTAMPTZ NOT NULL,
    event_count BIGINT NOT NULL CHECK (event_count > 0),
    late_event_count BIGINT NOT NULL CHECK (late_event_count >= 0 AND late_event_count <= event_count),
    avg_speed_kmh DOUBLE PRECISION,
    last_event_time TIMESTAMPTZ NOT NULL,
    last_latitude DOUBLE PRECISION NOT NULL CHECK (last_latitude BETWEEN -90 AND 90),
    last_longitude DOUBLE PRECISION NOT NULL CHECK (last_longitude BETWEEN -180 AND 180),
    row_sha256 TEXT NOT NULL,
    PRIMARY KEY (run_key, vehicle_id, hour_utc),
    CHECK (last_event_time >= hour_utc AND last_event_time < hour_utc + INTERVAL '1 hour')
);
CREATE INDEX IF NOT EXISTS ix_gps_hourly_curated_hour ON public.gps_hourly_curated (hour_utc);
