-- One row per content-addressed replay, vehicle and UTC hour.
-- Replays from different sources remain separate; no false cross-run deduplication.
{{ config(materialized='table', schema='marts') }}

SELECT
    gps_hour_key,
    run_key,
    source_sha256,
    vehicle_id,
    run_key || ':' || vehicle_id::text AS vehicle_run_key,
    TO_CHAR(hour_utc AT TIME ZONE 'UTC', 'YYYYMMDD') AS utc_date_key,
    hour_utc,
    event_count,
    late_event_count,
    CASE WHEN event_count > 0
        THEN ROUND(late_event_count::NUMERIC / event_count * 100, 2)
        ELSE NULL
    END AS late_event_rate_pct,
    avg_speed_kmh,
    last_event_time,
    last_latitude,
    last_longitude
FROM {{ ref('stg_gps_hourly') }}
