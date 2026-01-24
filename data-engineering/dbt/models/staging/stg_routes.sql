-- Staging model for routes
-- Cleans and calculates route metrics

{{ config(
    materialized='view',
    schema='staging'
) }}

WITH source_routes AS (
    SELECT
        id,
        route_date,
        driver_id,
        vehicle_id,
        depot_id,
        planned_distance_km,
        planned_duration_minutes,
        planned_stops,
        actual_distance_km,
        actual_duration_minutes,
        completed_stops,
        algorithm_used,
        optimization_score,
        computation_time_ms,
        status,
        started_at,
        completed_at,
        created_at,
        updated_at
    FROM {{ source('raw', 'routes') }}
)

SELECT
    -- Primary key
    id AS route_id,
    route_date,
    
    -- Foreign keys
    driver_id,
    vehicle_id,
    depot_id,
    
    -- Planned metrics
    CAST(planned_distance_km AS DECIMAL(10,2)) AS planned_distance_km,
    planned_duration_minutes,
    planned_stops,
    
    -- Actual metrics
    CAST(actual_distance_km AS DECIMAL(10,2)) AS actual_distance_km,
    actual_duration_minutes,
    completed_stops,
    
    -- Variance calculations
    CASE 
        WHEN planned_distance_km > 0 
        THEN ROUND((actual_distance_km - planned_distance_km) / planned_distance_km * 100, 2)
        ELSE 0
    END AS distance_variance_pct,
    
    CASE 
        WHEN planned_duration_minutes > 0 
        THEN ROUND((actual_duration_minutes - planned_duration_minutes)::DECIMAL / planned_duration_minutes * 100, 2)
        ELSE 0
    END AS duration_variance_pct,
    
    -- Completion rate
    CASE 
        WHEN planned_stops > 0 
        THEN ROUND(completed_stops::DECIMAL / planned_stops * 100, 2)
        ELSE 0
    END AS completion_rate_pct,
    
    -- Optimization
    algorithm_used,
    CAST(optimization_score AS DECIMAL(5,4)) AS optimization_score,
    computation_time_ms,
    
    -- Status
    status,
    
    -- Timing
    started_at,
    completed_at,
    CASE 
        WHEN completed_at IS NOT NULL AND started_at IS NOT NULL
        THEN EXTRACT(EPOCH FROM (completed_at - started_at)) / 60
        ELSE NULL
    END AS actual_total_minutes,
    
    -- Timestamps
    created_at,
    updated_at

FROM source_routes
