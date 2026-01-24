-- Driver performance dimension
-- Aggregated driver-level metrics for ranking and analysis

{{ config(
    materialized='table',
    schema='marts'
) }}

WITH driver_routes AS (
    SELECT
        driver_id,
        COUNT(*) AS total_routes,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_routes,
        SUM(completed_stops) AS total_completed_stops,
        SUM(actual_distance_km) AS total_distance_km,
        SUM(actual_duration_minutes) AS total_duration_minutes,
        AVG(completion_rate_pct) AS avg_completion_rate,
        AVG(distance_variance_pct) AS avg_distance_variance
    FROM {{ ref('stg_routes') }}
    WHERE driver_id IS NOT NULL
    GROUP BY driver_id
),

recent_performance AS (
    SELECT
        driver_id,
        AVG(completion_rate_pct) AS recent_completion_rate,
        COUNT(*) AS routes_last_30_days
    FROM {{ ref('stg_routes') }}
    WHERE route_date >= CURRENT_DATE - INTERVAL '30 days'
      AND driver_id IS NOT NULL
    GROUP BY driver_id
)

SELECT
    d.driver_id,
    d.employee_id,
    d.full_name,
    d.email,
    d.status,
    d.rating,
    d.rating_category,
    d.total_deliveries,
    d.license_status,
    d.max_working_hours,
    d.hire_date,
    
    -- Route metrics
    COALESCE(dr.total_routes, 0) AS total_routes,
    COALESCE(dr.completed_routes, 0) AS completed_routes,
    COALESCE(dr.total_completed_stops, 0) AS total_completed_stops,
    COALESCE(dr.total_distance_km, 0) AS total_distance_km,
    COALESCE(dr.total_duration_minutes, 0) AS total_duration_minutes,
    
    -- Averages
    COALESCE(dr.avg_completion_rate, 0) AS avg_completion_rate,
    COALESCE(dr.avg_distance_variance, 0) AS avg_distance_variance,
    
    -- Recent performance (last 30 days)
    COALESCE(rp.recent_completion_rate, 0) AS recent_completion_rate,
    COALESCE(rp.routes_last_30_days, 0) AS routes_last_30_days,
    
    -- Efficiency metrics
    CASE 
        WHEN dr.total_routes > 0 
        THEN ROUND(dr.total_completed_stops::DECIMAL / dr.total_routes, 1)
        ELSE 0 
    END AS avg_stops_per_route,
    
    CASE 
        WHEN dr.total_duration_minutes > 0 
        THEN ROUND(dr.total_distance_km / (dr.total_duration_minutes / 60), 1)
        ELSE 0 
    END AS avg_speed_kmh,
    
    -- Tenure
    EXTRACT(DAYS FROM CURRENT_DATE - d.hire_date) AS tenure_days,
    
    -- Ranking
    RANK() OVER (ORDER BY d.rating DESC, dr.avg_completion_rate DESC NULLS LAST) AS performance_rank,
    
    -- Metadata
    CURRENT_TIMESTAMP AS updated_at

FROM {{ ref('stg_drivers') }} d
LEFT JOIN driver_routes dr ON d.driver_id = dr.driver_id
LEFT JOIN recent_performance rp ON d.driver_id = rp.driver_id
