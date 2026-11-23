select event_id
from {{ ref('fct_deliveries') }}
where weight_kg < 0 or value_gbp < 0 or distance_km < 0
