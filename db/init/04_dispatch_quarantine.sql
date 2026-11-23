-- FleetFlow P1 Kafka poison-message quarantine.
-- Additive migration, applied AFTER db/init/03_dispatch_reliability.sql.
-- Run transactionally with psql -v ON_ERROR_STOP=1 -1. No auto-deploy.
CREATE TABLE IF NOT EXISTS dispatch_message_quarantine (
    id UUID PRIMARY KEY,
    topic VARCHAR(100) NOT NULL,
    partition INTEGER NOT NULL,
    kafka_offset BIGINT NOT NULL,
    payload_sha256 VARCHAR(64) NOT NULL,
    payload_bytes INTEGER NOT NULL,
    reason VARCHAR(80) NOT NULL,
    quarantined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_dispatch_quarantine_offset UNIQUE (topic, partition, kafka_offset),
    CONSTRAINT quarantine_digest_length CHECK (length(payload_sha256) = 64),
    CONSTRAINT quarantine_payload_length CHECK (payload_bytes >= 0)
);

-- The application role must not delete quarantine records during normal operation.
-- Retention and incident-review procedures require separate operational approval.
