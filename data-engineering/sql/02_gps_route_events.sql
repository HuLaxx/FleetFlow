CREATE TABLE IF NOT EXISTS public.gps_route_events (
 run_key TEXT NOT NULL, event_id UUID NOT NULL, route_id UUID NOT NULL,
 driver_id UUID NOT NULL, vehicle_id UUID NOT NULL, event_time TIMESTAMPTZ NOT NULL,
 latitude DOUBLE PRECISION NOT NULL CHECK(latitude BETWEEN -90 AND 90),
 longitude DOUBLE PRECISION NOT NULL CHECK(longitude BETWEEN -180 AND 180),
 PRIMARY KEY(run_key,event_id)
);
CREATE INDEX IF NOT EXISTS ix_gps_route_events_route ON public.gps_route_events(route_id);
