select
    {{ surrogate_key('depot_id') }} as depot_key,
    depot_id,
    depot_name,
    city,
    latitude,
    longitude
from {{ ref('stg_depots') }}
