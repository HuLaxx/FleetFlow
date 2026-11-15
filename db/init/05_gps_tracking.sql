-- Additive migration for real GPS freshness and event idempotency.
-- Apply after db/init/04_dispatch_quarantine.sql on a reviewed database.
-- No automatic production migrations are run by this PR.
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS last_gps_at TIMESTAMP;
ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS last_gps_event_id UUID;
CREATE INDEX IF NOT EXISTS ix_vehicles_last_gps_at ON vehicles(last_gps_at);
