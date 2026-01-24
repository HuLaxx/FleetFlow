-- Staging model for orders
-- Cleans and standardizes raw order data

{{ config(
    materialized='view',
    schema='staging'
) }}

WITH source_orders AS (
    SELECT
        id,
        order_number,
        customer_id,
        depot_id,
        items,
        total_weight_kg,
        total_value,
        delivery_date,
        time_window_start,
        time_window_end,
        service_time_minutes,
        status,
        priority,
        source,
        external_order_id,
        created_at,
        updated_at
    FROM {{ source('raw', 'orders') }}
)

SELECT
    -- Primary key
    id AS order_id,
    order_number,
    
    -- Foreign keys
    customer_id,
    depot_id,
    
    -- Order details
    items,
    CAST(total_weight_kg AS DECIMAL(10,2)) AS total_weight_kg,
    CAST(total_value AS DECIMAL(12,2)) AS total_value,
    
    -- Delivery timing
    delivery_date,
    time_window_start,
    time_window_end,
    service_time_minutes,
    
    -- Extract time components for analysis
    EXTRACT(HOUR FROM time_window_start) AS delivery_hour_start,
    EXTRACT(DOW FROM delivery_date) AS day_of_week,
    CASE 
        WHEN EXTRACT(DOW FROM delivery_date) IN (0, 6) THEN TRUE 
        ELSE FALSE 
    END AS is_weekend,
    
    -- Status and priority
    status,
    priority,
    CASE priority
        WHEN 1 THEN 'low'
        WHEN 2 THEN 'normal'
        WHEN 3 THEN 'high'
        WHEN 4 THEN 'urgent'
        WHEN 5 THEN 'critical'
    END AS priority_label,
    
    -- Source tracking
    source AS order_source,
    external_order_id,
    
    -- Timestamps
    created_at,
    updated_at,
    DATE(created_at) AS created_date

FROM source_orders
