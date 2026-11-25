-- =============================================================================
-- AgriResolve AI - PostgreSQL Database Schema
-- Master Relational DDL for Mandya Maddur Cluster Agricultural Decision Support
-- All tables include provenance tracking (data_type and is_synthetic)
-- =============================================================================

-- Extension for UUID generation if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- -----------------------------------------------------------------------------
-- 1. Table: rsk (Raitha Samparka Kendra Centers)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rsk (
    rsk_code VARCHAR(32) PRIMARY KEY,
    rsk_name VARCHAR(128) NOT NULL,
    taluk VARCHAR(64) NOT NULL,
    district VARCHAR(64) NOT NULL,
    state VARCHAR(64) NOT NULL DEFAULT 'Karnataka',
    latitude NUMERIC(8, 4) NOT NULL,
    longitude NUMERIC(8, 4) NOT NULL,
    contact_phone VARCHAR(32),
    data_type VARCHAR(16) NOT NULL DEFAULT 'Real',
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 2. Table: villages (Revenue Villages)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS villages (
    village_id VARCHAR(32) PRIMARY KEY,
    village_name VARCHAR(128) NOT NULL,
    lgd_code INTEGER UNIQUE NOT NULL,
    taluk VARCHAR(64) NOT NULL,
    district VARCHAR(64) NOT NULL,
    state VARCHAR(64) NOT NULL DEFAULT 'Karnataka',
    rsk_code VARCHAR(32) REFERENCES rsk(rsk_code) ON DELETE SET NULL,
    rsk_mapping_status VARCHAR(64) DEFAULT 'Simulated (Administrative Prototype)',
    latitude NUMERIC(8, 4) NOT NULL,
    longitude NUMERIC(8, 4) NOT NULL,
    total_area_hectares NUMERIC(10, 2) NOT NULL,
    cultivated_area_hectares NUMERIC(10, 2) NOT NULL,
    soil_type VARCHAR(64),
    primary_irrigation_source VARCHAR(128),
    major_crops VARCHAR(256),
    data_type VARCHAR(16) NOT NULL DEFAULT 'Real',
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_villages_lgd ON villages(lgd_code);
CREATE INDEX IF NOT EXISTS idx_villages_rsk ON villages(rsk_code);

-- -----------------------------------------------------------------------------
-- 3. Table: crops (Master Agricultural Catalog)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crops (
    crop_id VARCHAR(32) PRIMARY KEY,
    crop_name VARCHAR(64) NOT NULL,
    botanical_name VARCHAR(128),
    kannada_name VARCHAR(128),
    season VARCHAR(64),
    duration_days INTEGER,
    water_requirement_mm NUMERIC(8, 2),
    drought_sensitivity VARCHAR(32),
    pest_vulnerability VARCHAR(128),
    priority_economic_weight NUMERIC(4, 2) DEFAULT 0.50,
    data_type VARCHAR(16) NOT NULL DEFAULT 'Real',
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE
);

-- -----------------------------------------------------------------------------
-- 4. Table: village_crops (Crop Coverage & Normal Yields per Village)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS village_crops (
    id SERIAL PRIMARY KEY,
    village_id VARCHAR(32) REFERENCES villages(village_id) ON DELETE CASCADE,
    crop_id VARCHAR(32) REFERENCES crops(crop_id) ON DELETE CASCADE,
    sown_area_hectares NUMERIC(10, 2) NOT NULL,
    normal_yield_tons_per_ha NUMERIC(6, 2),
    data_type VARCHAR(16) NOT NULL DEFAULT 'Real',
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(village_id, crop_id)
);

-- -----------------------------------------------------------------------------
-- 5. Table: rainfall_observations (IMD / KSNDMC Gauge Series)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rainfall_observations (
    id SERIAL PRIMARY KEY,
    observation_date DATE NOT NULL,
    village_id VARCHAR(32) REFERENCES villages(village_id) ON DELETE CASCADE,
    actual_rainfall_mm NUMERIC(8, 2) NOT NULL CHECK (actual_rainfall_mm >= 0.0),
    normal_rainfall_mm NUMERIC(8, 2) NOT NULL CHECK (normal_rainfall_mm >= 0.0),
    rainfall_anomaly_mm NUMERIC(8, 2),
    rainfall_anomaly_percent NUMERIC(8, 2),
    rainfall_status VARCHAR(32),
    source_station VARCHAR(128),
    data_type VARCHAR(16) NOT NULL DEFAULT 'Real',
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(village_id, observation_date)
);

CREATE INDEX IF NOT EXISTS idx_rainfall_village_date ON rainfall_observations(village_id, observation_date);

-- -----------------------------------------------------------------------------
-- 6. Table: ndvi_observations (Sentinel-2 MSI Surface Reflectance)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ndvi_observations (
    id SERIAL PRIMARY KEY,
    observation_date DATE NOT NULL,
    village_id VARCHAR(32) REFERENCES villages(village_id) ON DELETE CASCADE,
    satellite VARCHAR(64) DEFAULT 'Sentinel-2 MSI (Level-2A)',
    tile_id VARCHAR(16) DEFAULT '43PGP',
    mean_ndvi NUMERIC(5, 3) NOT NULL CHECK (mean_ndvi >= -1.0 AND mean_ndvi <= 1.0),
    cloud_cover_percent NUMERIC(5, 2) NOT NULL,
    qa_flag VARCHAR(64),
    is_cloud_masked BOOLEAN DEFAULT FALSE,
    ndvi_delta NUMERIC(5, 3),
    ndvi_pct_change NUMERIC(6, 2),
    vegetation_stress_flag BOOLEAN DEFAULT FALSE,
    data_type VARCHAR(16) NOT NULL DEFAULT 'Real',
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(village_id, observation_date)
);

CREATE INDEX IF NOT EXISTS idx_ndvi_village_date ON ndvi_observations(village_id, observation_date);

-- -----------------------------------------------------------------------------
-- 7. Table: weather_observations (Real-time Google Weather / Open-Meteo)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weather_observations (
    id SERIAL PRIMARY KEY,
    observation_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    village_id VARCHAR(32) REFERENCES villages(village_id) ON DELETE CASCADE,
    temperature_celsius NUMERIC(5, 2),
    relative_humidity_percent NUMERIC(5, 2),
    wind_speed_kmh NUMERIC(5, 2),
    precipitation_prob_percent NUMERIC(5, 2),
    weather_condition VARCHAR(64),
    data_type VARCHAR(16) NOT NULL DEFAULT 'Real',
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE
);

-- -----------------------------------------------------------------------------
-- 8. Table: farmer_complaints (Reported Field Distress)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS farmer_complaints (
    complaint_id VARCHAR(32) PRIMARY KEY,
    village_id VARCHAR(32) REFERENCES villages(village_id) ON DELETE CASCADE,
    farmer_pseudonym VARCHAR(64) NOT NULL,
    survey_number VARCHAR(32),
    crop_affected VARCHAR(64) NOT NULL,
    issue_category VARCHAR(64) NOT NULL,
    issue_description TEXT,
    affected_area_hectares NUMERIC(6, 2) NOT NULL,
    urgency_level VARCHAR(32) NOT NULL CHECK (urgency_level IN ('Low', 'Medium', 'High', 'Critical')),
    reported_date DATE NOT NULL,
    status VARCHAR(32) DEFAULT 'Open',
    data_type VARCHAR(16) NOT NULL DEFAULT 'Synthetic',
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_complaints_village ON farmer_complaints(village_id);
CREATE INDEX IF NOT EXISTS idx_complaints_date ON farmer_complaints(reported_date);

-- -----------------------------------------------------------------------------
-- 9. Table: staff (RSK Agriculture Department Officers)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staff (
    staff_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    role VARCHAR(64) NOT NULL CHECK (role IN ('AO (Agriculture Officer)', 'AAO (Assistant Agriculture Officer)', 'AA (Agricultural Assistant)')),
    designation VARCHAR(128),
    jurisdiction VARCHAR(256),
    phone_masked VARCHAR(32),
    status VARCHAR(64) DEFAULT 'Available for Dispatch',
    active_inspections_count INTEGER DEFAULT 0,
    max_weekly_capacity INTEGER DEFAULT 8,
    data_type VARCHAR(16) NOT NULL DEFAULT 'Synthetic',
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE
);

-- -----------------------------------------------------------------------------
-- 10. Table: inspections_history (Past Field Inspections)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inspections_history (
    inspection_id VARCHAR(32) PRIMARY KEY,
    village_id VARCHAR(32) REFERENCES villages(village_id) ON DELETE CASCADE,
    inspection_date DATE NOT NULL,
    days_since_last_inspection INTEGER,
    inspecting_officer_id VARCHAR(32) REFERENCES staff(staff_id) ON DELETE SET NULL,
    field_observations TEXT,
    advisory_issued TEXT,
    resolution_status VARCHAR(64) DEFAULT 'Resolved',
    data_type VARCHAR(16) NOT NULL DEFAULT 'Synthetic',
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE
);

-- -----------------------------------------------------------------------------
-- 11. Table: assignments (AO Inspection Allocations to AAO/AA)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assignments (
    assignment_id VARCHAR(32) PRIMARY KEY,
    village_id VARCHAR(32) REFERENCES villages(village_id) ON DELETE CASCADE,
    assigned_by_staff_id VARCHAR(32) REFERENCES staff(staff_id),
    assigned_to_staff_id VARCHAR(32) REFERENCES staff(staff_id),
    priority_rank INTEGER,
    target_date DATE NOT NULL,
    status VARCHAR(32) DEFAULT 'Assigned' CHECK (status IN ('Assigned', 'In Progress', 'Completed', 'Cancelled')),
    special_instructions TEXT,
    data_type VARCHAR(16) NOT NULL DEFAULT 'Synthetic',
    is_synthetic BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 12. Table: monitoring_results (Routine & Reported Intermediate Scoring)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS monitoring_results (
    id SERIAL PRIMARY KEY,
    calculation_date DATE NOT NULL,
    village_id VARCHAR(32) REFERENCES villages(village_id) ON DELETE CASCADE,
    routine_flag BOOLEAN DEFAULT FALSE,
    routine_risk_score NUMERIC(5, 2),
    routine_explanation TEXT,
    reported_flag BOOLEAN DEFAULT FALSE,
    reported_severity_score NUMERIC(5, 2),
    reported_explanation TEXT,
    linked_complaints_count INTEGER DEFAULT 0,
    data_type VARCHAR(16) NOT NULL DEFAULT 'Derived',
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(village_id, calculation_date)
);

-- -----------------------------------------------------------------------------
-- 13. Table: priority_scores (Combined AI Prioritization)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS priority_scores (
    priority_id VARCHAR(32) PRIMARY KEY,
    calculation_date DATE NOT NULL,
    village_id VARCHAR(32) REFERENCES villages(village_id) ON DELETE CASCADE,
    combined_score NUMERIC(5, 2) NOT NULL,
    rank_order INTEGER NOT NULL,
    recommendation_action VARCHAR(64) NOT NULL,
    human_explanation TEXT NOT NULL,
    data_reliability_penalty NUMERIC(4, 2) DEFAULT 0.0,
    data_type VARCHAR(16) NOT NULL DEFAULT 'Derived',
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 14. Table: priority_score_factors (Transparent Explainable Breakdown)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS priority_score_factors (
    id SERIAL PRIMARY KEY,
    priority_id VARCHAR(32) REFERENCES priority_scores(priority_id) ON DELETE CASCADE,
    factor_name VARCHAR(64) NOT NULL,
    factor_raw_value NUMERIC(10, 2),
    factor_normalized_weight NUMERIC(4, 2),
    factor_weighted_score NUMERIC(5, 2),
    plain_language_contribution VARCHAR(256)
);

-- -----------------------------------------------------------------------------
-- 15. Table: data_reliability (Audit & Recency Indicators)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS data_reliability (
    village_id VARCHAR(32) PRIMARY KEY REFERENCES villages(village_id) ON DELETE CASCADE,
    total_satellite_passes INTEGER,
    clear_satellite_passes INTEGER,
    mean_cloud_cover_percent NUMERIC(5, 2),
    rainfall_observations_count INTEGER,
    data_completeness_ratio NUMERIC(5, 3),
    overall_reliability_score NUMERIC(4, 2),
    reliability_tier VARCHAR(32),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_type VARCHAR(16) NOT NULL DEFAULT 'Derived',
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE
);

-- -----------------------------------------------------------------------------
-- 16. Table: guideline_documents (Package of Practices for RAG Assistant)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS guideline_documents (
    doc_id VARCHAR(32) PRIMARY KEY,
    title VARCHAR(256) NOT NULL,
    source_organisation VARCHAR(128) NOT NULL,
    crop_name VARCHAR(64),
    category VARCHAR(64),
    file_path VARCHAR(256),
    sha256_hash VARCHAR(64),
    data_type VARCHAR(16) NOT NULL DEFAULT 'Real',
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE
);
