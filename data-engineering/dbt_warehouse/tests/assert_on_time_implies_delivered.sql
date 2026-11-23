select event_id
from {{ ref('fct_deliveries') }}
where is_on_time and not is_delivered
