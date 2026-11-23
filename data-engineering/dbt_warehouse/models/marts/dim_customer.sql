select
    {{ surrogate_key('customer_id') }} as customer_key,
    customer_id,
    city,
    segment
from {{ ref('stg_customers') }}
