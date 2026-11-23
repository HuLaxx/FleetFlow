-- Any date/order count mismatch makes dbt build fail.
WITH actual AS (
    SELECT
        delivery_date,
        COUNT(*) AS total_orders,
        COUNT(*) FILTER (WHERE status = 'delivered') AS delivered_orders
    FROM {{ source('raw', 'orders') }}
    GROUP BY delivery_date
)
SELECT
    COALESCE(a.delivery_date, d.date) AS date
FROM actual a
FULL OUTER JOIN {{ ref('fct_daily_performance') }} d
  ON a.delivery_date = d.date
WHERE COALESCE(a.total_orders, 0) <> d.total_orders
   OR COALESCE(a.delivered_orders, 0) <> d.delivered_orders
   OR d.date IS NULL
