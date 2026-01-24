-- ============================================
-- FleetFlow PostgreSQL + PostGIS Schema
-- ============================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- DEPOTS (Warehouses/Distribution Centers)
-- ============================================
CREATE TABLE depots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    latitude DECIMAL(10,7) NOT NULL,
    longitude DECIMAL(10,7) NOT NULL,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    capacity_vehicles INTEGER DEFAULT 50,
    operating_hours_start TIME DEFAULT '06:00:00',
    operating_hours_end TIME DEFAULT '22:00:00',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_depots_location ON depots USING GIST (location);

-- ============================================
-- DRIVERS
-- ============================================
CREATE TABLE drivers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    license_number VARCHAR(50),
    license_expiry DATE,
    home_location GEOGRAPHY(POINT, 4326),
    preferred_depot_id UUID REFERENCES depots(id),
    max_working_hours_per_day DECIMAL(4,2) DEFAULT 8.00,
    status VARCHAR(20) DEFAULT 'available' CHECK (status IN ('available', 'on_route', 'on_break', 'offline')),
    rating DECIMAL(3,2) DEFAULT 5.00,
    total_deliveries INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_drivers_status ON drivers(status);
CREATE INDEX idx_drivers_depot ON drivers(preferred_depot_id);

-- ============================================
-- VEHICLES
-- ============================================
CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vehicle_number VARCHAR(50) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (type IN ('van', 'truck', 'bike', 'car')),
    make VARCHAR(100),
    model VARCHAR(100),
    year INTEGER,
    capacity_kg DECIMAL(10,2) NOT NULL,
    capacity_cubic_m DECIMAL(10,2),
    fuel_type VARCHAR(20) DEFAULT 'diesel' CHECK (fuel_type IN ('diesel', 'petrol', 'electric', 'hybrid')),
    fuel_efficiency_km_per_l DECIMAL(5,2),
    co2_emission_g_per_km DECIMAL(6,2),
    depot_id UUID REFERENCES depots(id),
    current_driver_id UUID REFERENCES drivers(id),
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    current_location GEOGRAPHY(POINT, 4326),
    status VARCHAR(20) DEFAULT 'available' CHECK (status IN ('available', 'in_use', 'maintenance', 'retired')),
    last_maintenance_date DATE,
    next_maintenance_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_vehicles_status ON vehicles(status);
CREATE INDEX idx_vehicles_location ON vehicles USING GIST (current_location);

-- ============================================
-- CUSTOMERS
-- ============================================
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(100),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    address TEXT NOT NULL,
    latitude DECIMAL(10,7) NOT NULL,
    longitude DECIMAL(10,7) NOT NULL,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    delivery_instructions TEXT,
    preferred_time_window_start TIME,
    preferred_time_window_end TIME,
    priority INTEGER DEFAULT 1 CHECK (priority BETWEEN 1 AND 5),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_customers_location ON customers USING GIST (location);
CREATE INDEX idx_customers_external ON customers(external_id);

-- ============================================
-- ORDERS
-- ============================================
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id UUID REFERENCES customers(id),
    depot_id UUID REFERENCES depots(id),
    
    -- Order details
    items JSONB NOT NULL DEFAULT '[]',
    total_weight_kg DECIMAL(10,2) NOT NULL,
    total_value DECIMAL(12,2),
    
    -- Delivery requirements
    delivery_date DATE NOT NULL,
    time_window_start TIMESTAMPTZ NOT NULL,
    time_window_end TIMESTAMPTZ NOT NULL,
    service_time_minutes INTEGER DEFAULT 5,
    
    -- Status tracking
    status VARCHAR(30) DEFAULT 'pending' CHECK (status IN (
        'pending', 'assigned', 'in_transit', 'arrived', 
        'delivered', 'failed', 'cancelled', 'rescheduled'
    )),
    priority INTEGER DEFAULT 1 CHECK (priority BETWEEN 1 AND 5),
    
    -- Integration
    source VARCHAR(50) DEFAULT 'manual',
    external_order_id VARCHAR(100),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_date ON orders(delivery_date);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_depot ON orders(depot_id);

-- ============================================
-- ROUTES (Optimized Routes)
-- ============================================
CREATE TABLE routes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    route_date DATE NOT NULL,
    driver_id UUID REFERENCES drivers(id),
    vehicle_id UUID REFERENCES vehicles(id),
    depot_id UUID REFERENCES depots(id),
    
    -- Route geometry
    planned_route GEOGRAPHY(LINESTRING, 4326),
    actual_route GEOGRAPHY(LINESTRING, 4326),
    
    -- Metrics (planned)
    planned_distance_km DECIMAL(10,2),
    planned_duration_minutes INTEGER,
    planned_stops INTEGER,
    
    -- Metrics (actual)
    actual_distance_km DECIMAL(10,2),
    actual_duration_minutes INTEGER,
    completed_stops INTEGER DEFAULT 0,
    
    -- Optimization metadata
    algorithm_used VARCHAR(50),
    optimization_score DECIMAL(5,4),
    computation_time_ms INTEGER,
    
    -- Status
    status VARCHAR(20) DEFAULT 'planned' CHECK (status IN (
        'planned', 'in_progress', 'completed', 'cancelled'
    )),
    
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_routes_date ON routes(route_date);
CREATE INDEX idx_routes_driver ON routes(driver_id);
CREATE INDEX idx_routes_status ON routes(status);

-- ============================================
-- ROUTE STOPS (Individual Stops in a Route)
-- ============================================
CREATE TABLE route_stops (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    route_id UUID REFERENCES routes(id) ON DELETE CASCADE,
    order_id UUID REFERENCES orders(id),
    
    -- Sequence
    stop_sequence INTEGER NOT NULL,
    
    -- Location
    latitude DECIMAL(10,7) NOT NULL,
    longitude DECIMAL(10,7) NOT NULL,
    location GEOGRAPHY(POINT, 4326) NOT NULL,
    address TEXT NOT NULL,
    
    -- Timing (planned)
    planned_arrival TIMESTAMPTZ,
    planned_departure TIMESTAMPTZ,
    
    -- Timing (actual)
    actual_arrival TIMESTAMPTZ,
    actual_departure TIMESTAMPTZ,
    
    -- Distance from previous stop
    distance_from_prev_km DECIMAL(10,2),
    duration_from_prev_minutes INTEGER,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN (
        'pending', 'en_route', 'arrived', 'completed', 'skipped', 'failed'
    )),
    failure_reason TEXT,
    
    -- Proof of delivery
    signature_url TEXT,
    photo_url TEXT,
    recipient_name VARCHAR(255),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_route_stops_route ON route_stops(route_id);
CREATE INDEX idx_route_stops_order ON route_stops(order_id);
CREATE INDEX idx_route_stops_sequence ON route_stops(route_id, stop_sequence);

-- ============================================
-- DELIVERY ZONES (Geographic Service Areas)
-- ============================================
CREATE TABLE delivery_zones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    depot_id UUID REFERENCES depots(id),
    boundary GEOGRAPHY(POLYGON, 4326) NOT NULL,
    h3_resolution INTEGER DEFAULT 7,
    h3_cells TEXT[], -- Array of H3 cell IDs
    priority INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_zones_boundary ON delivery_zones USING GIST (boundary);
CREATE INDEX idx_zones_depot ON delivery_zones(depot_id);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to calculate distance between two points
CREATE OR REPLACE FUNCTION calculate_distance_km(
    lat1 DOUBLE PRECISION, lon1 DOUBLE PRECISION,
    lat2 DOUBLE PRECISION, lon2 DOUBLE PRECISION
) RETURNS DOUBLE PRECISION AS $$
BEGIN
    RETURN ST_Distance(
        ST_SetSRID(ST_MakePoint(lon1, lat1), 4326)::geography,
        ST_SetSRID(ST_MakePoint(lon2, lat2), 4326)::geography
    ) / 1000;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Sync latitude/longitude with geography point
CREATE OR REPLACE FUNCTION sync_location_columns()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
        IF NEW.location IS NULL THEN
            NEW.location = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::geography;
        END IF;
    ELSIF NEW.location IS NOT NULL THEN
        NEW.latitude = ST_Y(NEW.location::geometry);
        NEW.longitude = ST_X(NEW.location::geometry);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Sync latitude/longitude with vehicle current_location
CREATE OR REPLACE FUNCTION sync_current_location_columns()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
        IF NEW.current_location IS NULL THEN
            NEW.current_location = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::geography;
        END IF;
    ELSIF NEW.current_location IS NOT NULL THEN
        NEW.latitude = ST_Y(NEW.current_location::geometry);
        NEW.longitude = ST_X(NEW.current_location::geometry);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to find nearest depot
CREATE OR REPLACE FUNCTION find_nearest_depot(
    customer_lat DOUBLE PRECISION,
    customer_lon DOUBLE PRECISION
) RETURNS UUID AS $$
DECLARE
    nearest_depot_id UUID;
BEGIN
    SELECT id INTO nearest_depot_id
    FROM depots
    WHERE is_active = true
    ORDER BY location <-> ST_SetSRID(ST_MakePoint(customer_lon, customer_lat), 4326)::geography
    LIMIT 1;
    
    RETURN nearest_depot_id;
END;
$$ LANGUAGE plpgsql;

-- Function to find drivers within radius
CREATE OR REPLACE FUNCTION find_drivers_within_radius(
    center_lat DOUBLE PRECISION,
    center_lon DOUBLE PRECISION,
    radius_km DOUBLE PRECISION
) RETURNS TABLE (
    driver_id UUID,
    driver_name TEXT,
    distance_km DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id,
        d.first_name || ' ' || d.last_name,
        ST_Distance(
            v.current_location,
            ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326)::geography
        ) / 1000
    FROM drivers d
    JOIN vehicles v ON v.current_driver_id = d.id
    WHERE d.status = 'available'
      AND ST_DWithin(
          v.current_location,
          ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326)::geography,
          radius_km * 1000
      )
    ORDER BY 3;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- TRIGGERS
-- ============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables
CREATE TRIGGER update_depots_updated_at BEFORE UPDATE ON depots
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER sync_depots_location BEFORE INSERT OR UPDATE ON depots
    FOR EACH ROW EXECUTE FUNCTION sync_location_columns();

CREATE TRIGGER update_drivers_updated_at BEFORE UPDATE ON drivers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vehicles_updated_at BEFORE UPDATE ON vehicles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER sync_vehicles_location BEFORE INSERT OR UPDATE ON vehicles
    FOR EACH ROW EXECUTE FUNCTION sync_current_location_columns();

CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER sync_customers_location BEFORE INSERT OR UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION sync_location_columns();

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_routes_updated_at BEFORE UPDATE ON routes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_route_stops_updated_at BEFORE UPDATE ON route_stops
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER sync_route_stops_location BEFORE INSERT OR UPDATE ON route_stops
    FOR EACH ROW EXECUTE FUNCTION sync_location_columns();

-- ============================================
-- SEED DATA (Sample for Development)
-- ============================================

-- Sample depot
INSERT INTO depots (name, address, latitude, longitude, location, capacity_vehicles) VALUES
('NYC Main Hub', '123 Warehouse Ave, Brooklyn, NY 11201', 40.6892, -73.9857, ST_SetSRID(ST_MakePoint(-73.9857, 40.6892), 4326)::geography, 100),
('Manhattan Distribution', '456 Distribution Blvd, New York, NY 10001', 40.7505, -73.9934, ST_SetSRID(ST_MakePoint(-73.9934, 40.7505), 4326)::geography, 50),
('Jersey City Depot', '789 Logistics Way, Jersey City, NJ 07302', 40.7178, -74.0431, ST_SetSRID(ST_MakePoint(-74.0431, 40.7178), 4326)::geography, 75);

COMMIT;
