-- Additive, NULL-by-default dispatcher location scope. No auto-grants.
ALTER TABLE users ADD COLUMN IF NOT EXISTS depot_id UUID REFERENCES depots(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_users_depot_id ON users (depot_id);
-- Backfill dispatcher assignments only after human-approved authorization review.
