-- GeoAI Explorer PostGIS initialization
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Known thermal springs (Rhodope / SW Bulgaria seed data)
CREATE TABLE IF NOT EXISTS thermal_springs (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    geom GEOMETRY(Point, 4326) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_thermal_springs_geom
    ON thermal_springs USING GIST (geom);

INSERT INTO thermal_springs (name, geom) VALUES
    ('Велинград', ST_SetSRID(ST_MakePoint(23.9875, 41.9330), 4326)),
    ('Девин',     ST_SetSRID(ST_MakePoint(24.4013, 41.7375), 4326)),
    ('Сандански', ST_SetSRID(ST_MakePoint(23.2814, 41.5680), 4326)),
    ('Банкя',     ST_SetSRID(ST_MakePoint(23.1500, 42.7167), 4326));

-- Active faults (GEM-style simplified segments for SW Bulgaria / Rhodopes)
CREATE TABLE IF NOT EXISTS active_faults (
    id SERIAL PRIMARY KEY,
    name TEXT,
    source TEXT DEFAULT 'GEM Global Active Faults (seed subset)',
    geom GEOMETRY(LineString, 4326) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_active_faults_geom
    ON active_faults USING GIST (geom);

-- Representative fault segments near Rhodope / SW Bulgaria geothermal corridor
INSERT INTO active_faults (name, geom) VALUES
    ('Struma Fault Zone', ST_GeomFromText(
        'LINESTRING(22.90 41.35, 23.05 41.55, 23.20 41.70, 23.35 41.90, 23.45 42.10)',
        4326
    )),
    ('Mesta Fault Zone', ST_GeomFromText(
        'LINESTRING(23.60 41.40, 23.75 41.55, 23.90 41.70, 24.05 41.85, 24.20 42.00)',
        4326
    )),
    ('Rhodope Central Fault', ST_GeomFromText(
        'LINESTRING(24.00 41.50, 24.20 41.65, 24.40 41.80, 24.55 41.95, 24.70 42.10)',
        4326
    )),
    ('Maritsa Fault Zone', ST_GeomFromText(
        'LINESTRING(23.50 42.00, 23.80 42.05, 24.10 42.10, 24.40 42.15, 24.70 42.20)',
        4326
    )),
    ('West Rhodope Fault', ST_GeomFromText(
        'LINESTRING(23.30 41.80, 23.50 41.90, 23.70 42.00, 23.90 42.10, 24.10 42.20)',
        4326
    ));

-- Analysis runs audit table
CREATE TABLE IF NOT EXISTS analysis_runs (
    id UUID PRIMARY KEY,
    bbox GEOMETRY(Polygon, 4326) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    ndvi_mean DOUBLE PRECISION,
    lst_anomaly_c DOUBLE PRECISION,
    fault_proximity_m DOUBLE PRECISION,
    spring_distance_m DOUBLE PRECISION,
    score DOUBLE PRECISION,
    breakdown JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_runs_bbox
    ON analysis_runs USING GIST (bbox);
