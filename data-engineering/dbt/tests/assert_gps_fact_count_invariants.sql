-- dbt singular test: no negative or inflated late counts in the observed fact.
SELECT gps_hour_key
FROM {{ ref('fct_gps_hourly') }}
WHERE event_count <= 0
   OR late_event_count < 0
   OR late_event_count > event_count
   OR last_event_time < hour_utc
   OR last_event_time >= hour_utc + INTERVAL '1 hour'
