-- ============================================
-- FleetFlow TimescaleDB Schema
-- Real-time GPS and Traffic Time-Series Data
-- ============================================

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================
-- GPS LOGS (Real-time Driver Location)
-- ============================================
CREATE TABLE gps_logs (
    time TIMESTAMPTZ NOT NULL,
    driver_id UUID NOT NULL,
    vehicle_id UUID NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    speed_kmh DECIMAL(5,2),
    heading DECIMAL(5,2), -- degrees 0-360
    accuracy_m DECIMAL(6,2),
    altitude_m DECIMAL(8,2),
    battery_level INTEGER,
    is_moving BOOLEAN DEFAULT true
);

-- Convert to hypertable (time-series optimized)
SELECT create_hypertable('gps_logs', 'time', chunk_time_interval => INTERVAL '1 day');

-- Indexes for fast queries
CREATE INDEX idx_gps_logs_driver ON gps_logs (driver_id, time DESC);
CREATE INDEX idx_gps_logs_vehicle ON gps_logs (vehicle_id, time DESC);

-- Compression policy (compress after 7 days)
ALTER TABLE gps_logs SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'driver_id'
);
SELECT add_compression_policy('gps_logs', INTERVAL '7 days');

-- Retention policy (delete after 90 days)
SELECT add_retention_policy('gps_logs', INTERVAL '90 days');

-- ============================================
-- ORDER EVENTS (Event Sourcing)
-- ============================================
CREATE TABLE order_events (
    time TIMESTAMPTZ NOT NULL,
    order_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    actor_type VARCHAR(20), -- 'driver', 'dispatcher', 'system', 'customer'
    actor_id UUID,
    ip_address INET,
    user_agent TEXT
);

SELECT create_hypertable('order_events', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_order_events_order ON order_events (order_id, time DESC);
CREATE INDEX idx_order_events_type ON order_events (event_type, time DESC);

-- ============================================
-- TRAFFIC DATA (External API Integration)
-- ============================================
CREATE TABLE traffic_data (
    time TIMESTAMPTZ NOT NULL,
    segment_id VARCHAR(100) NOT NULL, -- road segment identifier
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    current_speed_kmh DECIMAL(5,2),
    free_flow_speed_kmh DECIMAL(5,2),
    congestion_level DECIMAL(3,2), -- 0.0 (no traffic) to 1.0 (standstill)
    delay_minutes DECIMAL(6,2),
    confidence DECIMAL(3,2),
    source VARCHAR(50) -- 'tomtom', 'here', 'osrm'
);

SELECT create_hypertable('traffic_data', 'time', chunk_time_interval => INTERVAL '1 hour');

CREATE INDEX idx_traffic_segment ON traffic_data (segment_id, time DESC);

-- Compression after 1 day (high volume)
ALTER TABLE traffic_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'segment_id'
);
SELECT add_compression_policy('traffic_data', INTERVAL '1 day');

-- Retention after 30 days (only need recent traffic)
SELECT add_retention_policy('traffic_data', INTERVAL '30 days');

-- ============================================
-- ROUTE OPTIMIZATION METRICS
-- ============================================
CREATE TABLE optimization_metrics (
    time TIMESTAMPTZ NOT NULL,
    route_id UUID NOT NULL,
    metric_type VARCHAR(50) NOT NULL, -- 'calculation_time', 'improvement', 'constraint_violation'
    value DOUBLE PRECISION NOT NULL,
    metadata JSONB
);

SELECT create_hypertable('optimization_metrics', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_opt_metrics_route ON optimization_metrics (route_id, time DESC);

-- ============================================
-- DRIVER PERFORMANCE (Aggregated Metrics)
-- ============================================
CREATE TABLE driver_performance (
    time TIMESTAMPTZ NOT NULL,
    driver_id UUID NOT NULL,
    deliveries_completed INTEGER DEFAULT 0,
    deliveries_failed INTEGER DEFAULT 0,
    total_distance_km DECIMAL(10,2) DEFAULT 0,
    total_duration_minutes INTEGER DEFAULT 0,
    on_time_percentage DECIMAL(5,2),
    avg_delivery_time_minutes DECIMAL(6,2),
    customer_rating DECIMAL(3,2)
);

SELECT create_hypertable('driver_performance', 'time', chunk_time_interval => INTERVAL '1 day');

CREATE INDEX idx_driver_perf ON driver_performance (driver_id, time DESC);

-- ============================================
-- CONTINUOUS AGGREGATES (Pre-computed Views)
-- ============================================

-- Hourly order volume per zone (for forecasting)
CREATE MATERIALIZED VIEW hourly_order_volume
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    COUNT(*) AS order_count,
    AVG(CASE WHEN event_type = 'delivered' THEN 1 ELSE 0 END) AS delivery_rate
FROM order_events
WHERE event_type IN ('created', 'delivered', 'failed')
GROUP BY bucket
WITH NO DATA;

SELECT add_continuous_aggregate_policy('hourly_order_volume',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

-- Daily driver performance summary
CREATE MATERIALIZED VIEW daily_driver_summary
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    driver_id,
    SUM(deliveries_completed) AS total_deliveries,
    SUM(total_distance_km) AS total_distance,
    AVG(on_time_percentage) AS avg_on_time
FROM driver_performance
GROUP BY bucket, driver_id
WITH NO DATA;

SELECT add_continuous_aggregate_policy('daily_driver_summary',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day');

COMMIT;
