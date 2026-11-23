-- One row per calendar day present in the delivery fact.
with days as (
    select distinct delivery_date as date_day from {{ ref('stg_deliveries') }}
)
select
    cast(replace(cast(date_day as varchar), '-', '') as integer) as date_key,
    date_day,
    year(date_day)      as year,
    quarter(date_day)   as quarter,
    month(date_day)     as month,
    monthname(date_day) as month_name,
    dayofweek(date_day) as day_of_week,
    dayname(date_day)   as day_name,
    case when dayname(date_day) in ('Sat', 'Sun', 'Saturday', 'Sunday') then true else false end as is_weekend
from days
