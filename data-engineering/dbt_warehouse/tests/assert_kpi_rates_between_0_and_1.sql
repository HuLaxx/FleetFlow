-- Fails if any KPI rate falls outside [0, 1].
select *
from {{ ref('fct_daily_depot_kpis') }}
where success_rate < 0 or success_rate > 1
   or on_time_rate < 0 or on_time_rate > 1
