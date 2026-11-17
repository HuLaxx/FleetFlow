-- Source from reconciled content-addressed Parquet import; no synthetic fallback.
{{ config(materialized='view', schema='staging') }}

SELECT
    run_key,
    source_sha256,
    vehicle_id,
    hour_utc,
    event_count,
    late_event_count,
    avg_speed_kmh,
    last_event_time,
    last_latitude,
    last_longitude,
    row_sha256,
    run_key || ':' || vehicle_id::text || ':' || TO_CHAR(hour_utc AT TIME ZONE 'UTC', 'YYYYMMDDHH24MI') AS gps_hour_key
FROM {{ source('raw', 'gps_hourly_curated') }}
