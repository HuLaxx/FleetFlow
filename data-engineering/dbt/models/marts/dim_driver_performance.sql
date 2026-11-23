-- Non-identifying driver performance mart; avoid personal contact fields.
{{ config(materialized='table', schema='marts') }}
WITH route_aggregates AS (
    SELECT
        driver_id,
        COUNT(*) AS total_routes,
        COUNT(*) FILTER (WHERE status = 'completed') AS completed_routes,
        SUM(completed_stops) AS completed_stops,
        SUM(actual_distance_km) FILTER (WHERE status = 'completed') AS observed_distance_km,
        SUM(actual_duration_minutes) FILTER (WHERE status = 'completed') AS observed_duration_minutes,
        AVG(completion_rate_pct) AS avg_stop_completion_pct
    FROM {{ ref('stg_routes') }}
    WHERE driver_id IS NOT NULL
    GROUP BY driver_id
)
SELECT
    d.driver_id,
    d.employee_id,
    d.status,
    d.rating,
    d.rating_category,
    d.total_deliveries,
    d.license_status,
    d.max_working_hours,
    COALESCE(r.total_routes, 0) AS total_routes,
    COALESCE(r.completed_routes, 0) AS completed_routes,
    COALESCE(r.completed_stops, 0) AS completed_stops,
    r.observed_distance_km,
    r.observed_duration_minutes,
    r.avg_stop_completion_pct,
    CASE WHEN r.observed_duration_minutes > 0 AND r.observed_distance_km IS NOT NULL
         THEN ROUND(
             r.observed_distance_km / (r.observed_duration_minutes / 60.0), 2
         )
         ELSE NULL END AS observed_speed_kmh
FROM {{ ref('stg_drivers') }} d
LEFT JOIN route_aggregates r ON r.driver_id = d.driver_id
