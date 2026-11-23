-- Native route identity survives from the accepted browser GPS event.
{{ config(materialized='table', schema='marts') }}
SELECT run_key || ':' || event_id::text AS gps_route_event_key,
 run_key,event_id,route_id,driver_id,vehicle_id,event_time,latitude,longitude
FROM {{ source('raw','gps_route_events') }}
