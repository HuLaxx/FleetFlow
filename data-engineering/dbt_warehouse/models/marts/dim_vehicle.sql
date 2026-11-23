select
    {{ surrogate_key('vehicle_id') }} as vehicle_key,
    vehicle_id,
    depot_id,
    vehicle_type,
    capacity_kg
from {{ ref('stg_vehicles') }}
