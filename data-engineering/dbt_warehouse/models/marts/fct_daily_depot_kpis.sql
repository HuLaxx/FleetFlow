-- Daily operational KPIs per depot, built on the star schema.
select
    f.date_key,
    f.delivery_date,
    dp.depot_id,
    dp.city,
    count(*)                                                        as attempts,
    sum(case when f.is_delivered then 1 else 0 end)                 as delivered,
    sum(case when f.is_on_time then 1 else 0 end)                   as delivered_on_time,
    round(avg(case when f.is_delivered then 1.0 else 0.0 end), 4)   as success_rate,
    round(sum(case when f.is_on_time then 1.0 else 0.0 end)
          / nullif(sum(case when f.is_delivered then 1 else 0 end), 0), 4) as on_time_rate,
    round(avg(f.lateness_minutes), 1)                               as avg_lateness_minutes,
    round(sum(f.distance_km), 1)                                    as total_distance_km,
    round(sum(f.value_gbp), 2)                                      as delivered_value_gbp
from {{ ref('fct_deliveries') }} f
join {{ ref('dim_depot') }} dp on f.depot_key = dp.depot_key
group by 1, 2, 3, 4
