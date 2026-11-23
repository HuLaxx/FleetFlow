-- Grain: one row per delivery attempt (event_id).
-- Incremental: only re-processes the trailing `lookback_days` so late-arriving events are merged
-- without rebuilding history. unique_key makes re-runs idempotent.
{{ config(
    materialized='incremental',
    unique_key='event_id',
    incremental_strategy='delete+insert',
    on_schema_change='fail'
) }}

select
    d.event_id,
    d.order_id,
    d.order_number,
    cast(replace(cast(d.delivery_date as varchar), '-', '') as integer) as date_key,
    {{ surrogate_key('d.depot_id') }}    as depot_key,
    {{ surrogate_key('d.vehicle_id') }}  as vehicle_key,
    {{ surrogate_key('d.driver_id') }}   as driver_key,
    {{ surrogate_key('d.customer_id') }} as customer_key,
    d.delivery_date,
    d.attempted_at,
    d.status,
    d.is_delivered,
    d.is_on_time,
    d.lateness_minutes,
    d.ingest_latency_minutes,
    d.weight_kg,
    d.value_gbp,
    d.priority,
    d.distance_km
from {{ ref('stg_deliveries') }} d
{% if is_incremental() %}
where d.delivery_date >= (
    select {{ dbt.dateadd('day', -var('lookback_days'), 'max(delivery_date)') }} from {{ this }}
)
{% endif %}
