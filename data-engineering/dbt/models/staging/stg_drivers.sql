-- Analytical staging intentionally omits names, emails, telephone numbers and addresses.
{{ config(materialized='view', schema='staging') }}
SELECT
    id AS driver_id,
    employee_id,
    preferred_depot_id,
    CAST(max_working_hours_per_day AS DECIMAL(4,2)) AS max_working_hours,
    status,
    status = 'available' AS is_available,
    CAST(rating AS DECIMAL(3,2)) AS rating,
    total_deliveries,
    CASE
        WHEN rating IS NULL THEN 'unrated'
        WHEN rating >= 4.8 THEN 'excellent'
        WHEN rating >= 4.5 THEN 'good'
        WHEN rating >= 4.0 THEN 'average'
        ELSE 'needs_improvement'
    END AS rating_category,
    CASE
        WHEN license_expiry IS NULL THEN 'unknown'
        WHEN license_expiry < CURRENT_DATE THEN 'expired'
        WHEN license_expiry < CURRENT_DATE + INTERVAL '30 days' THEN 'expiring_soon'
        ELSE 'valid'
    END AS license_status,
    created_at,
    updated_at
FROM {{ source('raw', 'drivers') }}
