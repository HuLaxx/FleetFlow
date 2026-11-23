-- SYNTHETIC recovery: real status updates; the schema's update_*_updated_at
-- triggers stamp updated_at = now(), so every SLA should pass afterwards.
\set ON_ERROR_STOP on
UPDATE route_stops SET status = 'completed' WHERE route_id = '00000000-0000-0000-0000-0000000000f1';
UPDATE drivers SET status = 'on_route' WHERE id = '00000000-0000-0000-0000-0000000000d1';
