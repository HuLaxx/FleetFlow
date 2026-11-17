-- One row per delivery date, including dates with routes but zero orders.
-- Count metrics may safely be 0. Ratios/actuals have NULL when unobserved.
{{ config(materialized='table', schema='marts') }}

WITH daily_orders AS (
    SELECT
        delivery_date,
        COUNT(*) AS total_orders,
        COUNT(*) FILTER (WHERE status = 'delivered') AS delivered_orders,
        COUNT(*) FILTER (WHERE status = 'failed') AS failed_orders,
        COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled_orders,
        SUM(total_weight_kg) AS total_weight_kg,
        SUM(total_value) AS total_revenue,
        COUNT(*) FILTER (WHERE priority >= 4) AS high_priority_orders
    FROM {{ ref('stg_orders') }}
    GROUP BY delivery_date
),
daily_routes AS (
    SELECT
        route_date AS delivery_date,
        COUNT(*) AS total_routes,
        COUNT(*) FILTER (WHERE status = 'completed') AS completed_routes,
        SUM(planned_distance_km) AS total_planned_distance_km,
        SUM(actual_distance_km) FILTER (
            WHERE status = 'completed' AND actual_distance_km IS NOT NULL
        ) AS total_actual_distance_km,
        SUM(planned_distance_km) FILTER (
            WHERE status = 'completed'
              AND actual_distance_km IS NOT NULL
              AND planned_distance_km > 0
        ) AS comparable_planned_distance_km,
        SUM(actual_distance_km) FILTER (
            WHERE status = 'completed'
              AND actual_distance_km IS NOT NULL
              AND planned_distance_km > 0
        ) AS comparable_actual_distance_km,
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
    COALESCE(o.total_orders, 0) AS total_orders,
    COALESCE(o.delivered_orders, 0) AS delivered_orders,
    COALESCE(o.failed_orders, 0) AS failed_orders,
    COALESCE(o.cancelled_orders, 0) AS cancelled_orders,
    CASE WHEN o.total_orders > 0
         THEN ROUND(o.delivered_orders::DECIMAL / o.total_orders * 100, 2)
         ELSE NULL END AS delivery_success_rate_pct,
    o.total_weight_kg,
    o.total_revenue,
    COALESCE(o.high_priority_orders, 0) AS high_priority_orders,
    COALESCE(r.total_routes, 0) AS total_routes,
    COALESCE(r.completed_routes, 0) AS completed_routes,
    r.total_planned_distance_km,
    r.total_actual_distance_km,
    CASE WHEN r.comparable_planned_distance_km > 0
         THEN ROUND(
             r.comparable_actual_distance_km / r.comparable_planned_distance_km * 100, 2
         )
         ELSE NULL END AS observed_vs_planned_distance_pct,
    COALESCE(r.total_planned_stops, 0) AS total_planned_stops,
    COALESCE(r.total_completed_stops, 0) AS total_completed_stops,
    CASE WHEN r.total_planned_stops > 0
         THEN ROUND(r.total_completed_stops::DECIMAL / r.total_planned_stops * 100, 2)
         ELSE NULL END AS stop_completion_rate_pct,
    r.avg_optimization_score,
    r.avg_computation_time_ms,
    COALESCE(dd.active_drivers, 0) AS active_drivers,
    dd.avg_driver_rating,
    CASE WHEN dd.active_drivers > 0
         THEN ROUND(o.total_orders::DECIMAL / dd.active_drivers, 1)
         ELSE NULL END AS orders_per_active_driver
FROM daily_orders o
FULL OUTER JOIN daily_routes r ON o.delivery_date = r.delivery_date
LEFT JOIN daily_drivers dd ON dd.delivery_date = COALESCE(o.delivery_date, r.delivery_date)
