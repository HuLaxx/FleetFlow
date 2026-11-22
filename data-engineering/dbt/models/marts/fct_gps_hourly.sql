-- One row per content-addressed replay, vehicle and UTC hour.
-- Dimension joins are left joins: never silently drop an observed fact.
-- Explicit ref() parents ensure dbt build --select +fct_gps_hourly builds dimensions.
{{ config(materialized='table', schema='marts') }}

WITH observed AS (
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
)
SELECT
    observed.gps_hour_key,
    observed.run_key,
    observed.source_sha256,
    observed.vehicle_id,
    observed.vehicle_run_key,
    observed.utc_date_key,
    observed.hour_utc,
    observed.event_count,
    observed.late_event_count,
    observed.late_event_rate_pct,
    observed.avg_speed_kmh,
    observed.last_event_time,
    observed.last_latitude,
    observed.last_longitude
FROM observed
LEFT JOIN {{ ref('dim_observed_vehicle') }} AS vehicles
  ON observed.vehicle_run_key = vehicles.vehicle_run_key
LEFT JOIN {{ ref('dim_utc_date') }} AS dates
  ON observed.utc_date_key = dates.utc_date_key
