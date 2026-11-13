-- FleetFlow P1 durability milestone, applied AFTER 01_postgis_schema.sql.
-- Existing installations must apply this explicit additive migration before use.
-- Run with psql -v ON_ERROR_STOP=1 -1 -f db/init/03_dispatch_reliability.sql.
-- This script does not create infrastructure or touch production automatically.

ALTER TABLE routes DROP CONSTRAINT IF EXISTS routes_status_check;
ALTER TABLE routes ADD CONSTRAINT routes_status_check
    CHECK (status IN ('planned', 'approved', 'in_progress', 'completed', 'cancelled'));

CREATE TABLE IF NOT EXISTS route_approval_audit (
    id UUID PRIMARY KEY,
    route_id UUID NOT NULL UNIQUE REFERENCES routes(id) ON DELETE RESTRICT,
    approved_by_user_id UUID NOT NULL,
    event_id UUID NOT NULL UNIQUE,
    previous_status VARCHAR(20) NOT NULL,
    new_status VARCHAR(20) NOT NULL,
    approved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT approval_transition_check
        CHECK (previous_status = 'planned' AND new_status = 'approved')
);

CREATE TABLE IF NOT EXISTS dispatch_outbox (
    id UUID PRIMARY KEY,
    topic VARCHAR(100) NOT NULL,
    message_key VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at TIMESTAMPTZ,
    last_error VARCHAR(150),
    CONSTRAINT dispatch_outbox_status_check CHECK (status IN ('pending', 'published'))
);

CREATE INDEX IF NOT EXISTS ix_dispatch_outbox_ready
    ON dispatch_outbox (status, next_attempt_at);

CREATE TABLE IF NOT EXISTS dispatch_consumer_inbox (
    consumer_name VARCHAR(100) NOT NULL,
    event_id UUID NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (consumer_name, event_id)
);

-- Append-only is a *database* guarantee, not a convention in Python.
CREATE OR REPLACE FUNCTION reject_route_approval_audit_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Route approval audit is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS route_approval_audit_immutable ON route_approval_audit;
CREATE TRIGGER route_approval_audit_immutable
    BEFORE UPDATE OR DELETE ON route_approval_audit
    FOR EACH ROW EXECUTE FUNCTION reject_route_approval_audit_mutation();
