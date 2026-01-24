-- Staging model for drivers
-- Cleans and calculates driver metrics

{{ config(
    materialized='view',
    schema='staging'
) }}

WITH source_drivers AS (
    SELECT
        id,
        employee_id,
        first_name,
        last_name,
        email,
        phone,
        license_number,
        license_expiry,
        preferred_depot_id,
        max_working_hours_per_day,
        status,
        rating,
        total_deliveries,
        created_at,
        updated_at
    FROM {{ source('raw', 'drivers') }}
)

SELECT
    -- Primary key
    id AS driver_id,
    employee_id,
    
    -- Name
    first_name,
    last_name,
    CONCAT(first_name, ' ', last_name) AS full_name,
    
    -- Contact
    email,
    phone,
    
    -- License
    license_number,
    license_expiry,
    CASE 
        WHEN license_expiry < CURRENT_DATE THEN 'expired'
        WHEN license_expiry < CURRENT_DATE + INTERVAL '30 days' THEN 'expiring_soon'
        ELSE 'valid'
    END AS license_status,
    
    -- Preferences
    preferred_depot_id,
    CAST(max_working_hours_per_day AS DECIMAL(4,2)) AS max_working_hours,
    
    -- Current status
    status,
    CASE status
        WHEN 'available' THEN TRUE
        ELSE FALSE
    END AS is_available,
    
    -- Performance metrics
    CAST(rating AS DECIMAL(3,2)) AS rating,
    total_deliveries,
    
    -- Rating category
    CASE 
        WHEN rating >= 4.8 THEN 'excellent'
        WHEN rating >= 4.5 THEN 'good'
        WHEN rating >= 4.0 THEN 'average'
        ELSE 'needs_improvement'
    END AS rating_category,
    
    -- Timestamps
    created_at,
    updated_at,
    DATE(created_at) AS hire_date

FROM source_drivers
