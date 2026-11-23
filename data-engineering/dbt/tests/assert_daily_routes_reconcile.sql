WITH actual AS (
    SELECT route_date,
           COUNT(*) AS total_routes,
           COUNT(*) FILTER (WHERE status='completed') AS completed_routes,
           COALESCE(SUM(planned_stops),0) AS planned_stops,
           COALESCE(SUM(completed_stops),0) AS completed_stops
    FROM {{ source('raw', 'routes') }}
    GROUP BY route_date
)
SELECT COALESCE(a.route_date, d.date) AS date
FROM actual a
FULL OUTER JOIN {{ ref('fct_daily_performance') }} d
    ON a.route_date=d.date
WHERE COALESCE(a.total_routes,0) <> d.total_routes
   OR COALESCE(a.completed_routes,0) <> d.completed_routes
   OR COALESCE(a.planned_stops,0) <> d.total_planned_stops
   OR COALESCE(a.completed_stops,0) <> d.total_completed_stops
   OR d.date IS NULL
