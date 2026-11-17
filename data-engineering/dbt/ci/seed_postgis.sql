-- Deterministic synthetic records in disposable fleetflow_test only.
-- Apply after src.database.Base.metadata.create_all. Never run in a real DB.
DO $$
BEGIN
    IF current_database() <> 'fleetflow_test' OR current_user <> 'fleetflow' THEN
        RAISE EXCEPTION 'Refusing dbt CI fixture outside local fleetflow_test';
    END IF;
END
$$;

INSERT INTO drivers (id, employee_id, first_name, last_name, email,
                     status, rating, total_deliveries, max_working_hours_per_day)
VALUES
('11111111-1111-4111-8111-111111111111','DBT-001','Synthetic','Driver',
 'dbt-fixture@example.test','available',4.50,1,8.00);

INSERT INTO orders
(id, order_number, items, total_weight_kg, total_value, delivery_date,
 time_window_start, time_window_end, service_time_minutes, status, priority)
VALUES
('22222222-2222-4222-8222-222222222221','DBT-ORD-001','[]'::jsonb,4.50,25.00,
 '2026-11-12','2026-11-12 10:00:00','2026-11-12 12:00:00',5,'delivered',4),
('22222222-2222-4222-8222-222222222222','DBT-ORD-002','[]'::jsonb,2.00,NULL,
 '2026-11-12','2026-11-12 13:00:00','2026-11-12 15:00:00',5,'pending',2);

INSERT INTO routes
(id, route_date, driver_id, planned_distance_km,
 planned_duration_minutes, planned_stops, actual_distance_km,
 actual_duration_minutes, completed_stops, algorithm_used, status,
 started_at, completed_at)
VALUES
('33333333-3333-4333-8333-333333333331','2026-11-12',
 '11111111-1111-4111-8111-111111111111',12.00,40,1,15.00,55,1,
 'synthetic-ci-only','completed','2026-11-12 10:00:00','2026-11-12 10:55:00'),
('33333333-3333-4333-8333-333333333332','2026-11-12',
 '11111111-1111-4111-8111-111111111111',20.00,70,2,NULL,NULL,0,
 'synthetic-ci-only','approved',NULL,NULL),
('33333333-3333-4333-8333-333333333333','2026-11-13',
 '11111111-1111-4111-8111-111111111111',18.00,60,2,NULL,NULL,0,
 'synthetic-ci-only','planned',NULL,NULL);
