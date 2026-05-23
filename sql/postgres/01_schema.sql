-- ═══════════════════════════════════════════════════════
--  MCS 504 DATABASE PROJECT — POSTGRESQL + POSTGIS SCHEMA
--  Idempotent Script: Runs on initialization
-- ═══════════════════════════════════════════════════════

-- Enable spatial and search extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ═══════════════════════════════════════════════════════
--  DROP EXISTING OBJECTS TO ENSURE IDEMPOTENCY
-- ═══════════════════════════════════════════════════════
DROP TABLE IF EXISTS stand_allocations_audit CASCADE;
DROP TABLE IF EXISTS stand_allocations CASCADE;
DROP TABLE IF EXISTS dependents CASCADE;
DROP TABLE IF EXISTS stand_owners CASCADE;
DROP TABLE IF EXISTS stand_subdivisions CASCADE;
DROP TABLE IF EXISTS stand_survey CASCADE;
DROP TABLE IF EXISTS stands CASCADE;
DROP TABLE IF EXISTS metadata_catalogue CASCADE;

DROP VIEW IF EXISTS vw_allocated_stands CASCADE;
DROP VIEW IF EXISTS vw_owner_portfolio CASCADE;
DROP MATERIALIZED VIEW IF EXISTS vw_disability_summary CASCADE;

DROP FUNCTION IF EXISTS sp_allocate_stand CASCADE;
DROP FUNCTION IF EXISTS sp_owner_report CASCADE;
DROP FUNCTION IF EXISTS sp_available_subdivisions CASCADE;

-- ═══════════════════════════════════════════════════════
--  1. TABLE CREATIONS & CONSTRAINTS (POSTGIS ENABLED)
-- ═══════════════════════════════════════════════════════

-- Entity 1: stands (PostGIS Polygon coordinates)
CREATE TABLE stands (
    stand_number VARCHAR(20) NOT NULL PRIMARY KEY,
    location VARCHAR(200) NOT NULL,
    size_m2 DECIMAL(12,2) NOT NULL,
    activity VARCHAR(50) NOT NULL,
    picture_url VARCHAR(500),
    gps_coordinates GEOMETRY(Polygon, 4326) NOT NULL,
    location_city VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_stands_size CHECK (size_m2 > 0),
    CONSTRAINT chk_stands_activity CHECK (activity IN ('Residential', 'Commercial'))
);

COMMENT ON TABLE stands IS 'Core land stands database with spatial boundaries';
COMMENT ON COLUMN stands.gps_coordinates IS 'PostGIS 2D Polygon boundary of the land stand';

-- Entity 2: stand_survey
CREATE TABLE stand_survey (
    survey_id SERIAL PRIMARY KEY,
    stand_number VARCHAR(20) NOT NULL,
    survey_status BOOLEAN NOT NULL DEFAULT FALSE,
    province VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_survey_stand FOREIGN KEY (stand_number) 
        REFERENCES stands (stand_number) ON DELETE CASCADE ON UPDATE CASCADE
);

COMMENT ON TABLE stand_survey IS 'Official state land surveys';

-- Entity 3: stand_subdivisions
CREATE TABLE stand_subdivisions (
    subdivision_id SERIAL PRIMARY KEY,
    stand_number VARCHAR(20) NOT NULL,
    allocation_status BOOLEAN NOT NULL DEFAULT FALSE,
    size_m2 DECIMAL(10,2) NOT NULL,
    remarks TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_subdivisions_stand FOREIGN KEY (stand_number) 
        REFERENCES stands (stand_number) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_subdivision_size CHECK (size_m2 > 0)
);

COMMENT ON TABLE stand_subdivisions IS 'Sub-plots partitioned from surveyed stands';

-- Entity 4: stand_owners
CREATE TABLE stand_owners (
    stand_owner_id SERIAL PRIMARY KEY,
    firstname VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(10) NOT NULL,
    disability_status BOOLEAN NOT NULL DEFAULT FALSE,
    province VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_owners_gender CHECK (gender IN ('Male', 'Female', 'Other'))
);

COMMENT ON TABLE stand_owners IS 'Registered stand owners (Confidential PII)';
COMMENT ON COLUMN stand_owners.firstname IS 'PII: Owner first name';
COMMENT ON COLUMN stand_owners.date_of_birth IS 'PII: Owner birth date';

-- Entity 5: dependents
CREATE TABLE dependents (
    dependent_id SERIAL PRIMARY KEY,
    stand_owner_id INT NOT NULL,
    firstname VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(10) NOT NULL,
    disability_status BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_dependents_owner FOREIGN KEY (stand_owner_id) 
        REFERENCES stand_owners (stand_owner_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_dependents_gender CHECK (gender IN ('Male', 'Female', 'Other'))
);

COMMENT ON TABLE dependents IS 'Registered dependants of stand owners';

-- Entity 6: stand_allocations
CREATE TABLE stand_allocations (
    allocation_id SERIAL PRIMARY KEY,
    stand_owner_id INT NOT NULL,
    subdivision_id INT NOT NULL,
    date_of_allocation DATE NOT NULL,
    price_per_m2 DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_allocations_owner FOREIGN KEY (stand_owner_id) 
        REFERENCES stand_owners (stand_owner_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_allocations_subdivision FOREIGN KEY (subdivision_id) 
        REFERENCES stand_subdivisions (subdivision_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_allocations_price CHECK (price_per_m2 > 0)
);

-- Audit Table
CREATE TABLE stand_allocations_audit (
    audit_id SERIAL PRIMARY KEY,
    action_type VARCHAR(10) NOT NULL,
    allocation_id INT NOT NULL,
    stand_owner_id INT NOT NULL,
    subdivision_id INT NOT NULL,
    date_of_allocation DATE NOT NULL,
    price_per_m2 DECIMAL(10,2) NOT NULL,
    changed_by VARCHAR(100) NOT NULL,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- ═══════════════════════════════════════════════════════
--  2. METADATA CATALOGUE TABLE
-- ═══════════════════════════════════════════════════════
CREATE TABLE metadata_catalogue (
    table_name VARCHAR(100) NOT NULL,
    column_name VARCHAR(100) NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    is_pii BOOLEAN DEFAULT FALSE,
    data_classification VARCHAR(50) DEFAULT 'Internal',
    data_owner VARCHAR(100) DEFAULT 'Ministry of Lands',
    data_steward VARCHAR(100) DEFAULT 'GIS Department',
    PRIMARY KEY (table_name, column_name)
);


-- ═══════════════════════════════════════════════════════
--  3. VIEWS & MATERIALIZED VIEWS CREATION
-- ═══════════════════════════════════════════════════════

-- View 1: Allocated Stands
CREATE OR REPLACE VIEW vw_allocated_stands AS
SELECT 
    sa.allocation_id,
    s.stand_number,
    s.location AS stand_location,
    sub.subdivision_id,
    sub.size_m2 AS sub_size_m2,
    so.stand_owner_id,
    so.firstname AS owner_name,
    so.disability_status,
    sa.date_of_allocation,
    (sub.size_m2 * sa.price_per_m2) AS total_allocation_price
FROM stand_allocations sa
JOIN stand_subdivisions sub ON sa.subdivision_id = sub.subdivision_id
JOIN stands s ON sub.stand_number = s.stand_number
JOIN stand_owners so ON sa.stand_owner_id = so.stand_owner_id;

-- View 2: Owner Portfolio
CREATE OR REPLACE VIEW vw_owner_portfolio AS
SELECT 
    so.stand_owner_id,
    so.firstname AS owner_name,
    so.province,
    COUNT(sa.allocation_id) AS stands_held_count,
    SUM(sub.size_m2) AS total_m2_owned,
    SUM(sub.size_m2 * sa.price_per_m2) AS total_portfolio_value
FROM stand_owners so
LEFT JOIN stand_allocations sa ON so.stand_owner_id = sa.stand_owner_id
LEFT JOIN stand_subdivisions sub ON sa.subdivision_id = sub.subdivision_id
GROUP BY so.stand_owner_id, so.firstname, so.province;

-- View 3: Materialized View for Disability Summary
CREATE MATERIALIZED VIEW vw_disability_summary AS
SELECT 
    p.province,
    COALESCE(owner_stats.disabled_owners_count, 0) AS disabled_owners_count,
    COALESCE(dep_stats.disabled_dependents_count, 0) AS disabled_dependents_count
FROM (
    SELECT DISTINCT province FROM stand_owners
    UNION 
    SELECT DISTINCT province FROM stand_survey
) p
LEFT JOIN (
    SELECT province, COUNT(*) AS disabled_owners_count
    FROM stand_owners 
    WHERE disability_status = TRUE 
    GROUP BY province
) owner_stats ON p.province = owner_stats.province
LEFT JOIN (
    SELECT so.province, COUNT(*) AS disabled_dependents_count
    FROM dependents d
    JOIN stand_owners so ON d.stand_owner_id = so.stand_owner_id
    WHERE d.disability_status = TRUE
    GROUP BY so.province
) dep_stats ON p.province = dep_stats.province;

CREATE UNIQUE INDEX idx_disability_mv_province ON vw_disability_summary(province);


-- ═══════════════════════════════════════════════════════
--  4. TRIGGERS & FUNCTIONS
-- ═══════════════════════════════════════════════════════

-- Trigger 1 Function: Audit Logs
CREATE OR REPLACE FUNCTION fn_audit_allocations()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO stand_allocations_audit 
        (action_type, allocation_id, stand_owner_id, subdivision_id, date_of_allocation, price_per_m2, changed_by)
        VALUES ('INSERT', NEW.allocation_id, NEW.stand_owner_id, NEW.subdivision_id, NEW.date_of_allocation, NEW.price_per_m2, current_user);
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO stand_allocations_audit 
        (action_type, allocation_id, stand_owner_id, subdivision_id, date_of_allocation, price_per_m2, changed_by)
        VALUES ('UPDATE', NEW.allocation_id, NEW.stand_owner_id, NEW.subdivision_id, NEW.date_of_allocation, NEW.price_per_m2, current_user);
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO stand_allocations_audit 
        (action_type, allocation_id, stand_owner_id, subdivision_id, date_of_allocation, price_per_m2, changed_by)
        VALUES ('DELETE', OLD.allocation_id, OLD.stand_owner_id, OLD.subdivision_id, OLD.date_of_allocation, OLD.price_per_m2, current_user);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_allocations
AFTER INSERT OR UPDATE OR DELETE ON stand_allocations
FOR EACH ROW EXECUTE FUNCTION fn_audit_allocations();


-- Trigger 2 Function: Check Subdivision Size & Survey Status
CREATE OR REPLACE FUNCTION fn_check_subdivision_size()
RETURNS TRIGGER AS $$
DECLARE
    parent_size DECIMAL(12,2);
    current_sum DECIMAL(12,2);
    survey_exists BOOLEAN;
BEGIN
    -- Business Rule: A stand must have an active survey status verified before subdividing.
    SELECT EXISTS (
        SELECT 1 FROM stand_survey 
        WHERE stand_number = NEW.stand_number AND survey_status = TRUE
    ) INTO survey_exists;
    
    IF NOT survey_exists THEN
        RAISE EXCEPTION 'Business Rule Violation: A stand must have an active survey status verified before subdividing.';
    END IF;

    -- Fetch parent size
    SELECT size_m2 INTO parent_size FROM stands WHERE stand_number = NEW.stand_number;
    
    -- Sum existing subdivision sizes
    SELECT COALESCE(SUM(size_m2), 0) INTO current_sum 
    FROM stand_subdivisions 
    WHERE stand_number = NEW.stand_number;
    
    IF (current_sum + NEW.size_m2) > parent_size THEN
        RAISE EXCEPTION 'Business Rule Violation: Total subdivisions size exceeds parent stand capacity.';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_check_subdivision_size
BEFORE INSERT ON stand_subdivisions
FOR EACH ROW EXECUTE FUNCTION fn_check_subdivision_size();


-- Trigger 3 Function: Allocation Status Handler
CREATE OR REPLACE FUNCTION fn_allocation_status()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        UPDATE stand_subdivisions 
        SET allocation_status = TRUE 
        WHERE subdivision_id = NEW.subdivision_id;
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        UPDATE stand_subdivisions 
        SET allocation_status = FALSE 
        WHERE subdivision_id = OLD.subdivision_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_allocation_status
AFTER INSERT OR DELETE ON stand_allocations
FOR EACH ROW EXECUTE FUNCTION fn_allocation_status();


-- ═══════════════════════════════════════════════════════
--  5. STORED PROCEDURES (FUNCTION RETURNS RECORD/REF_CURSOR)
-- ═══════════════════════════════════════════════════════

-- Proc 1: Allocation Transaction Manager
CREATE OR REPLACE FUNCTION sp_allocate_stand(
    p_owner_id INT,
    p_subdivision_id INT,
    p_price_per_m2 DECIMAL
) RETURNS VOID AS $$
DECLARE
    v_already_allocated BOOLEAN;
    v_is_owner_valid BOOLEAN;
    v_is_sub_valid BOOLEAN;
BEGIN
    -- Check Owner
    SELECT EXISTS (SELECT 1 FROM stand_owners WHERE stand_owner_id = p_owner_id) INTO v_is_owner_valid;
    IF NOT v_is_owner_valid THEN
        RAISE EXCEPTION 'Validation Error: Owner ID is not registered.';
    END IF;

    -- Check Subdivision
    SELECT EXISTS (SELECT 1 FROM stand_subdivisions WHERE subdivision_id = p_subdivision_id) INTO v_is_sub_valid;
    IF NOT v_is_sub_valid THEN
        RAISE EXCEPTION 'Validation Error: Subdivision ID does not exist.';
    END IF;

    -- Validate Price
    IF p_price_per_m2 <= 0 THEN
        RAISE EXCEPTION 'Validation Error: Price per m2 must be positive.';
    END IF;

    -- Check already allocated
    SELECT allocation_status INTO v_already_allocated FROM stand_subdivisions WHERE subdivision_id = p_subdivision_id;
    IF v_already_allocated THEN
        RAISE EXCEPTION 'Business Rule Violation: This subdivision is already allocated.';
    END IF;

    -- Insert record (Triggers will automatically set status to True)
    INSERT INTO stand_allocations (stand_owner_id, subdivision_id, date_of_allocation, price_per_m2)
    VALUES (p_owner_id, p_subdivision_id, CURRENT_DATE, p_price_per_m2);
    
    -- Refresh Materialized view
    REFRESH MATERIALIZED VIEW CONCURRENTLY vw_disability_summary;
END;
$$ LANGUAGE plpgsql;


-- Proc 2: Owner Portfolio Report Function
CREATE OR REPLACE FUNCTION sp_owner_report(p_owner_id INT)
RETURNS TABLE (
    stand_owner_id INT,
    firstname VARCHAR,
    province VARCHAR,
    district VARCHAR,
    allocation_id INT,
    date_of_allocation DATE,
    price_per_m2 DECIMAL,
    subdivision_id INT,
    size_m2 DECIMAL,
    stand_number VARCHAR,
    location VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        so.stand_owner_id,
        so.firstname,
        so.province,
        so.district,
        sa.allocation_id,
        sa.date_of_allocation,
        sa.price_per_m2,
        sub.subdivision_id,
        sub.size_m2,
        s.stand_number,
        s.location
    FROM stand_owners so
    LEFT JOIN stand_allocations sa ON so.stand_owner_id = sa.stand_owner_id
    LEFT JOIN stand_subdivisions sub ON sa.subdivision_id = sub.subdivision_id
    LEFT JOIN stands s ON sub.stand_number = s.stand_number
    WHERE so.stand_owner_id = p_owner_id;
END;
$$ LANGUAGE plpgsql;


-- Proc 3: Available subdivisions listing
CREATE OR REPLACE FUNCTION sp_available_subdivisions(
    p_province VARCHAR,
    p_district VARCHAR
) RETURNS TABLE (
    subdivision_id INT,
    stand_number VARCHAR,
    size_m2 DECIMAL,
    remarks TEXT,
    province VARCHAR,
    district VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sub.subdivision_id,
        sub.stand_number,
        sub.size_m2,
        sub.remarks,
        sur.province,
        sur.district
    FROM stand_subdivisions sub
    JOIN stand_survey sur ON sub.stand_number = sur.stand_number
    WHERE sub.allocation_status = FALSE
      AND sur.province = p_province
      AND sur.district = p_district;
END;
$$ LANGUAGE plpgsql;


-- ═══════════════════════════════════════════════════════
--  6. OPTIMISATIONS & INDEXING (GiST SPATIAL INDEX)
-- ═══════════════════════════════════════════════════════

-- 1. PostGIS spatial index (GiST) on geometry boundary polygon
CREATE INDEX idx_stands_spatial ON stands USING GIST(gps_coordinates);

-- 2. Composite Index on locations
CREATE INDEX idx_survey_postgres_loc ON stand_survey (province, district);
CREATE INDEX idx_owners_postgres_loc ON stand_owners (province, district);

-- 3. Filtered Index (Partial Index) on unallocated subdivisions
CREATE INDEX idx_subdivisions_partial_unallocated 
ON stand_subdivisions (subdivision_id, size_m2) 
WHERE allocation_status = FALSE;

-- 4. Text search index using pg_trgm for location names
CREATE INDEX idx_stands_location_trgm ON stands USING gin (location gin_trgm_ops);


-- ═══════════════════════════════════════════════════════
--  7. DATA PROTECTION & RLS (ROW LEVEL SECURITY)
-- ═══════════════════════════════════════════════════════

-- Define roles
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'land_readonly') THEN
        CREATE ROLE land_readonly WITH LOGIN PASSWORD 'ReadPass123!';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'land_app') THEN
        CREATE ROLE land_app WITH LOGIN PASSWORD 'AppPassword123!';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'land_admin') THEN
        CREATE ROLE land_admin WITH SUPERUSER LOGIN PASSWORD 'Admin1234!';
    END IF;
END $$;

-- Enable Row Level Security on stand_owners
ALTER TABLE stand_owners ENABLE ROW LEVEL SECURITY;

-- Owner policy: owners only see their own records, but app/admin can query all records based on custom settings.
CREATE POLICY owner_policy ON stand_owners 
    FOR ALL 
    USING (
        (current_setting('app.current_user_role', true) = 'land_admin') OR 
        (current_setting('app.current_user_role', true) = 'land_app') OR 
        (stand_owner_id = current_setting('app.current_owner_id', true)::integer)
    );

-- Table Permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO land_readonly;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO land_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO land_app;

-- ═══════════════════════════════════════════════════════
--  8. SEED DATA GENERATION (ZIMBABWE PLACE NAMES)
-- ═══════════════════════════════════════════════════════

INSERT INTO stands (stand_number, location, size_m2, activity, picture_url, gps_coordinates, location_city) VALUES
('STD-HAR-001', 'Borrowdale Brooke Golf Estate, Section A', 4000.00, 'Residential', 'http://images.lands.gov.zw/stands/std-har-001.png', ST_GeomFromText('POLYGON((31.111 -17.722, 31.115 -17.722, 31.115 -17.726, 31.111 -17.726, 31.111 -17.722))', 4326), 'Harare'),
('STD-BUL-002', 'Suburbs Road Near Ascot Mall', 3000.00, 'Residential', 'http://images.lands.gov.zw/stands/std-bul-002.png', ST_GeomFromText('POLYGON((28.601 -20.155, 28.605 -20.155, 28.605 -20.159, 28.601 -20.159, 28.601 -20.155))', 4326), 'Bulawayo'),
('STD-MUT-003', 'Chitepo Main Street Boulevard Commercial Hub', 7500.00, 'Commercial', 'http://images.lands.gov.zw/stands/std-mut-003.png', ST_GeomFromText('POLYGON((32.668 -18.971, 32.674 -18.971, 32.674 -18.976, 32.668 -18.976, 32.668 -18.971))', 4326), 'Mutare'),
('STD-GWE-004', 'Senga Industrial Area Main Bypass', 12000.00, 'Commercial', 'http://images.lands.gov.zw/stands/std-gwe-004.png', ST_GeomFromText('POLYGON((29.831 -19.461, 29.841 -19.461, 29.841 -19.469, 29.831 -19.469, 29.831 -19.461))', 4326), 'Gweru'),
('STD-MAS-005', 'Rhodene High-density Layout Block D', 2500.00, 'Residential', 'http://images.lands.gov.zw/stands/std-mas-005.png', ST_GeomFromText('POLYGON((30.825 -20.065, 30.829 -20.065, 30.829 -20.069, 30.825 -20.069, 30.825 -20.065))', 4326), 'Masvingo');

INSERT INTO stand_survey (stand_number, survey_status, province, district) VALUES
('STD-HAR-001', TRUE, 'Harare', 'Harare Central'),
('STD-BUL-002', TRUE, 'Bulawayo', 'Bulawayo Central'),
('STD-MUT-003', TRUE, 'Manicaland', 'Mutare'),
('STD-GWE-004', TRUE, 'Midlands', 'Gweru'),
('STD-MAS-005', TRUE, 'Masvingo', 'Masvingo');

INSERT INTO stand_subdivisions (stand_number, allocation_status, size_m2, remarks) VALUES
('STD-HAR-001', FALSE, 1500.00, 'Divided Brooke plot East Wing'),
('STD-HAR-001', FALSE, 2000.00, 'Divided Brooke plot West Wing'),
('STD-BUL-002', FALSE, 1200.00, 'Ascot subdiv Sector 1'),
('STD-BUL-002', FALSE, 1500.00, 'Ascot subdiv Sector 2'),
('STD-MUT-003', FALSE, 3500.00, 'Commercial plaza division North'),
('STD-MUT-003', FALSE, 3000.00, 'Commercial plaza division South'),
('STD-GWE-004', FALSE, 6000.00, 'Senga Heavy Yard Subdivision A'),
('STD-MAS-005', FALSE, 1000.00, 'Rhodene Corner Lot A'),
('STD-MAS-005', FALSE, 1200.00, 'Rhodene Corner Lot B');

INSERT INTO stand_owners (firstname, date_of_birth, gender, disability_status, province, district) VALUES
('Tendai Mupfumi', '1980-04-12', 'Male', FALSE, 'Harare', 'Harare Central'),
('Chipo Sibanda', '1988-11-23', 'Female', TRUE, 'Bulawayo', 'Bulawayo Central'),
('Farai Mutasa', '1975-06-30', 'Male', FALSE, 'Manicaland', 'Mutare'),
('Nyarai Zhou', '1992-01-15', 'Female', FALSE, 'Midlands', 'Gweru'),
('Tinashe Moyo', '1982-08-05', 'Male', TRUE, 'Masvingo', 'Masvingo');

INSERT INTO dependents (stand_owner_id, firstname, date_of_birth, gender, disability_status) VALUES
(1, 'Rufaro Mupfumi', '2010-05-14', 'Female', FALSE),
(1, 'Kundai Mupfumi', '2015-09-20', 'Male', FALSE),
(2, 'Lindiwe Sibanda', '2012-03-04', 'Female', TRUE),
(3, 'Tariro Mutasa', '2008-07-22', 'Female', FALSE),
(5, 'Tatenda Moyo', '2014-12-01', 'Male', FALSE);

-- Call Allocation Stored Procedures using SQL statements
SELECT sp_allocate_stand(1, 1, 150.00);
SELECT sp_allocate_stand(2, 3, 120.00);
SELECT sp_allocate_stand(3, 5, 200.00);
SELECT sp_allocate_stand(4, 7, 85.00);
SELECT sp_allocate_stand(5, 8, 110.00);

-- Refresh Materialized view
REFRESH MATERIALIZED VIEW CONCURRENTLY vw_disability_summary;

-- Populate Data Catalogue Table manually for compliance
INSERT INTO metadata_catalogue (table_name, column_name, data_type, is_pii, data_classification) VALUES
('stands', 'stand_number', 'VARCHAR', FALSE, 'Public'),
('stands', 'gps_coordinates', 'GEOMETRY', FALSE, 'Internal'),
('stand_owners', 'firstname', 'VARCHAR', TRUE, 'Confidential'),
('stand_owners', 'date_of_birth', 'DATE', TRUE, 'Confidential'),
('stand_owners', 'gender', 'VARCHAR', TRUE, 'Confidential'),
('stand_owners', 'disability_status', 'BOOLEAN', TRUE, 'Confidential'),
('dependents', 'firstname', 'VARCHAR', TRUE, 'Confidential'),
('dependents', 'date_of_birth', 'DATE', TRUE, 'Confidential');
