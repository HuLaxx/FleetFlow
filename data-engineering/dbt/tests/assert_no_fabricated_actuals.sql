-- A route with zero observed actual distance contributes no numeric actual.
SELECT date
FROM {{ ref('fct_daily_performance') }}
WHERE (completed_routes = 0 AND total_actual_distance_km IS NOT NULL)
   OR (completed_routes = 0 AND observed_vs_planned_distance_pct IS NOT NULL)
   OR (total_routes = 0 AND stop_completion_rate_pct IS NOT NULL)
   OR (total_orders = 0 AND delivery_success_rate_pct IS NOT NULL)
   OR (active_drivers = 0 AND orders_per_active_driver IS NOT NULL)
   OR (total_completed_stops > total_planned_stops)
