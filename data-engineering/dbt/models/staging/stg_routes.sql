-- P2: honest operational semantics, source is the current PostGIS OLTP table.
-- A planned/approved route is not a completed route or observed distance.
{{ config(materialized='view', schema='staging') }}

SELECT
    id AS route_id,
    route_date,
    driver_id,
    vehicle_id,
    depot_id,
    CAST(planned_distance_km AS DECIMAL(10,2)) AS planned_distance_km,
    planned_duration_minutes,
    planned_stops,
    CAST(actual_distance_km AS DECIMAL(10,2)) AS actual_distance_km,
    actual_duration_minutes,
    completed_stops,
    CASE
        WHEN planned_distance_km > 0 AND actual_distance_km IS NOT NULL
        THEN ROUND((actual_distance_km - planned_distance_km) / planned_distance_km * 100, 2)
        ELSE NULL
    END AS distance_variance_pct,
    CASE
        WHEN planned_duration_minutes > 0 AND actual_duration_minutes IS NOT NULL
        THEN ROUND(
            (actual_duration_minutes - planned_duration_minutes)::DECIMAL
            / planned_duration_minutes * 100, 2
        )
        ELSE NULL
    END AS duration_variance_pct,
    CASE
        WHEN planned_stops > 0
        THEN ROUND(completed_stops::DECIMAL / planned_stops * 100, 2)
        ELSE NULL
    END AS completion_rate_pct,
    algorithm_used,
    CAST(optimization_score AS DECIMAL(5,4)) AS optimization_score,
    computation_time_ms,
    status,
    started_at,
    completed_at,
    CASE
        WHEN started_at IS NOT NULL AND completed_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (completed_at - started_at)) / 60
        ELSE NULL
    END AS actual_total_minutes,
    created_at,
    updated_at
FROM {{ source('raw', 'routes') }}
