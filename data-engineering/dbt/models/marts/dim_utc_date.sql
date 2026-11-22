-- Only calendar dates observed in content-addressed replay data.
-- UTC conversion is explicit: session/database local time does not shift the date.
{{ config(materialized='table', schema='marts') }}

WITH observed_dates AS (
    SELECT DISTINCT (hour_utc AT TIME ZONE 'UTC')::date AS utc_date
    FROM {{ ref('stg_gps_hourly') }}
)
SELECT
    TO_CHAR(utc_date, 'YYYYMMDD') AS utc_date_key,
    utc_date,
    EXTRACT(YEAR FROM utc_date)::INTEGER AS calendar_year,
    EXTRACT(MONTH FROM utc_date)::INTEGER AS calendar_month,
    EXTRACT(DAY FROM utc_date)::INTEGER AS calendar_day,
    EXTRACT(ISODOW FROM utc_date)::INTEGER AS iso_day_of_week
FROM observed_dates
