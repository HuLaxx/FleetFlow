-- SYNTHETIC CI scenario for `dbt source freshness`.
-- Runs after db/init/01_postgis_schema.sql (which seeds three depots).
-- Timestamps are relative to now() so the expected verdicts are deterministic:
--   orders       newest created_at  1h ago  -> pass  (warn 6h,  error 24h)
--   routes       newest updated_at  3h ago  -> pass  (warn 24h, error 48h)
--   drivers      newest updated_at 30h ago  -> warn  (warn 24h, error 72h)
--   route_stops  newest updated_at 50h ago  -> error (warn 24h, error 48h)
-- INSERTs keep the explicit timestamps; the update_*_updated_at triggers only
-- fire on UPDATE (see refresh_scenario.sql).
\set ON_ERROR_STOP on
BEGIN;

INSERT INTO customers (id, name, address, latitude, longitude, location, created_at, updated_at)
VALUES ('00000000-0000-0000-0000-0000000000c1', 'Synthetic Customer', '1 Test Street', 40.70, -73.99,
        ST_SetSRID(ST_MakePoint(-73.99, 40.70), 4326)::geography, now() - interval '200 hours', now() - interval '200 hours');

INSERT INTO drivers (id, employee_id, first_name, last_name, email, preferred_depot_id, created_at, updated_at)
SELECT '00000000-0000-0000-0000-0000000000d1', 'SYN-001', 'Synthetic', 'Driver', 'driver@example.invalid', id,
       now() - interval '200 hours', now() - interval '30 hours'
FROM depots ORDER BY name LIMIT 1;

INSERT INTO vehicles (id, vehicle_number, type, capacity_kg, depot_id, created_at, updated_at)
SELECT '00000000-0000-0000-0000-0000000000e1', 'SYN-VAN-1', 'van', 800, id,
       now() - interval '200 hours', now() - interval '200 hours'
FROM depots ORDER BY name LIMIT 1;

INSERT INTO orders (id, order_number, customer_id, depot_id, total_weight_kg, delivery_date,
                    time_window_start, time_window_end, created_at, updated_at)
SELECT ('00000000-0000-0000-0000-00000000010' || n)::uuid, 'SYN-ORD-' || n, '00000000-0000-0000-0000-0000000000c1',
       d.id, 10 * n, current_date, now(), now() + interval '2 hours',
       now() - (n || ' hours')::interval, now() - (n || ' hours')::interval
FROM generate_series(1, 3) AS n, (SELECT id FROM depots ORDER BY name LIMIT 1) AS d;

INSERT INTO routes (id, route_date, driver_id, vehicle_id, depot_id, status, created_at, updated_at)
SELECT '00000000-0000-0000-0000-0000000000f1', current_date, '00000000-0000-0000-0000-0000000000d1',
       '00000000-0000-0000-0000-0000000000e1', id, 'in_progress', now() - interval '3 hours', now() - interval '3 hours'
FROM depots ORDER BY name LIMIT 1;

INSERT INTO route_stops (route_id, order_id, stop_sequence, latitude, longitude, location, address, created_at, updated_at)
VALUES ('00000000-0000-0000-0000-0000000000f1', '00000000-0000-0000-0000-000000000101', 1, 40.70, -73.99,
        ST_SetSRID(ST_MakePoint(-73.99, 40.70), 4326)::geography, '1 Test Street',
        now() - interval '50 hours', now() - interval '50 hours');

COMMIT;
