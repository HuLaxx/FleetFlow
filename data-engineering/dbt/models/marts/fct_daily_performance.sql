-- Daily delivery performance mart
-- Aggregated daily metrics for dashboards and reporting

{{ config(
    materialized='table',
    schema='marts'
) }}

WITH daily_orders AS (
    SELECT
        delivery_date,
        COUNT(*) AS total_orders,
        SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) AS delivered_orders,
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_orders,
        SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_orders,
        SUM(total_weight_kg) AS total_weight_kg,
        SUM(total_value) AS total_value,
        AVG(service_time_minutes) AS avg_service_time_minutes,
        SUM(CASE WHEN priority >= 4 THEN 1 ELSE 0 END) AS high_priority_orders
    FROM {{ ref('stg_orders') }}
    GROUP BY delivery_date
),

daily_routes AS (
    SELECT
        route_date AS delivery_date,
        COUNT(*) AS total_routes,
        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_routes,
        SUM(planned_distance_km) AS total_planned_distance_km,
        SUM(actual_distance_km) AS total_actual_distance_km,
        SUM(planned_stops) AS total_planned_stops,
        SUM(completed_stops) AS total_completed_stops,
        AVG(optimization_score) AS avg_optimization_score,
        AVG(computation_time_ms) AS avg_computation_time_ms
    FROM {{ ref('stg_routes') }}
    GROUP BY route_date
),

daily_drivers AS (
    SELECT
        r.route_date AS delivery_date,
        COUNT(DISTINCT r.driver_id) AS active_drivers,
        AVG(d.rating) AS avg_driver_rating
    FROM {{ ref('stg_routes') }} r
    LEFT JOIN {{ ref('stg_drivers') }} d ON r.driver_id = d.driver_id
    WHERE r.status IN ('in_progress', 'completed')
    GROUP BY r.route_date
)

SELECT
    COALESCE(o.delivery_date, r.delivery_date) AS date,
    
    -- Order metrics
    COALESCE(o.total_orders, 0) AS total_orders,
    COALESCE(o.delivered_orders, 0) AS delivered_orders,
    COALESCE(o.failed_orders, 0) AS failed_orders,
    COALESCE(o.cancelled_orders, 0) AS cancelled_orders,
    
    -- Delivery success rate
    CASE 
        WHEN o.total_orders > 0 
        THEN ROUND(o.delivered_orders::DECIMAL / o.total_orders * 100, 2)
        ELSE 0 
    END AS delivery_success_rate,
    
    -- Order value
    COALESCE(o.total_weight_kg, 0) AS total_weight_kg,
    COALESCE(o.total_value, 0) AS total_revenue,
    COALESCE(o.high_priority_orders, 0) AS high_priority_orders,
    
    -- Route metrics
    COALESCE(r.total_routes, 0) AS total_routes,
    COALESCE(r.completed_routes, 0) AS completed_routes,
    COALESCE(r.total_planned_distance_km, 0) AS total_planned_distance_km,
    COALESCE(r.total_actual_distance_km, 0) AS total_actual_distance_km,
    
    -- Distance efficiency
    CASE 
        WHEN r.total_planned_distance_km > 0 
        THEN ROUND((r.total_actual_distance_km / r.total_planned_distance_km) * 100, 2)
        ELSE 100 
    END AS distance_efficiency_pct,
    
    -- Stop completion
    COALESCE(r.total_planned_stops, 0) AS total_planned_stops,
    COALESCE(r.total_completed_stops, 0) AS total_completed_stops,
    CASE 
        WHEN r.total_planned_stops > 0 
        THEN ROUND(r.total_completed_stops::DECIMAL / r.total_planned_stops * 100, 2)
        ELSE 0 
    END AS stop_completion_rate,
    
    -- Optimization
    COALESCE(r.avg_optimization_score, 0) AS avg_optimization_score,
    COALESCE(r.avg_computation_time_ms, 0) AS avg_computation_time_ms,
    
    -- Driver metrics
    COALESCE(dd.active_drivers, 0) AS active_drivers,
    COALESCE(dd.avg_driver_rating, 0) AS avg_driver_rating,
    
    -- Derived metrics
    CASE 
        WHEN dd.active_drivers > 0 
        THEN ROUND(o.total_orders::DECIMAL / dd.active_drivers, 1)
        ELSE 0 
    END AS orders_per_driver,
    
    CASE 
        WHEN dd.active_drivers > 0 
        THEN ROUND(r.total_actual_distance_km / dd.active_drivers, 2)
        ELSE 0 
    END AS distance_per_driver_km,
    
    -- Metadata
    CURRENT_TIMESTAMP AS updated_at

FROM daily_orders o
FULL OUTER JOIN daily_routes r ON o.delivery_date = r.delivery_date
LEFT JOIN daily_drivers dd ON COALESCE(o.delivery_date, r.delivery_date) = dd.delivery_date
