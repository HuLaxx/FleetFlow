SELECT route_id
FROM {{ ref('stg_routes') }}
WHERE (actual_distance_km IS NULL AND distance_variance_pct IS NOT NULL)
   OR (actual_duration_minutes IS NULL AND duration_variance_pct IS NOT NULL)
   OR completed_stops > planned_stops
   OR completed_stops < 0
