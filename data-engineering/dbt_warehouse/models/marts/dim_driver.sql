select
    {{ surrogate_key('driver_id') }} as driver_key,
    driver_id,
    employee_id,
    depot_id,
    cast(hired_date as date) as hired_date,
    rating,
    case when rating >= 4.5 then 'top' when rating >= 4.0 then 'good' else 'developing' end as rating_band
from {{ ref('stg_drivers') }}
