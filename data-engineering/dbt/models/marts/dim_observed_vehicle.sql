-- Observed vehicles only: one row per immutable replay and vehicle.
-- This is NOT a complete operational fleet master or availability dimension.
{{ config(materialized='table', schema='marts') }}

SELECT
    run_key || ':' || vehicle_id::text AS vehicle_run_key,
    run_key,
    vehicle_id,
    MIN(hour_utc) AS first_observed_hour_utc,
    MAX(hour_utc) AS last_observed_hour_utc,
    SUM(event_count) AS observed_event_count,
    SUM(late_event_count) AS observed_late_event_count
FROM {{ ref('stg_gps_hourly') }}
GROUP BY run_key, vehicle_id
