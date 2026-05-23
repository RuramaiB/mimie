-- ═══════════════════════════════════════════════════════
--  MCS 504 DATABASE PROJECT — MS SQL SERVER SCHEMA
--  Idempotent Script: Runs on database initialization
-- ═══════════════════════════════════════════════════════

USE devdb;
GO

-- Configure Query Store for Performance Monitoring (Q7 Requirement)
IF NOT EXISTS (SELECT * FROM sys.database_query_store_options)
BEGIN
    ALTER DATABASE devdb SET QUERY_STORE = ON;
END
GO

-- ═══════════════════════════════════════════════════════
--  DROP EXISTING SCHEMAS & POLICIES
-- ═══════════════════════════════════════════════════════
IF EXISTS (SELECT * FROM sys.security_policies WHERE name = 'OwnerFilter')
BEGIN
    DROP SECURITY POLICY OwnerFilter;
END
GO

IF EXISTS (SELECT * FROM sys.objects WHERE name = 'fn_securitypredicate' AND type = 'IF')
BEGIN
    DROP FUNCTION dbo.fn_securitypredicate;
END
GO

IF EXISTS (SELECT * FROM sys.objects WHERE name = 'stand_allocations_audit' AND type = 'U')
    DROP TABLE stand_allocations_audit;
IF EXISTS (SELECT * FROM sys.objects WHERE name = 'stand_allocations' AND type = 'U')
    DROP TABLE stand_allocations;
IF EXISTS (SELECT * FROM sys.objects WHERE name = 'dependents' AND type = 'U')
    DROP TABLE dependents;
IF EXISTS (SELECT * FROM sys.objects WHERE name = 'stand_owners' AND type = 'U')
    DROP TABLE stand_owners;
IF EXISTS (SELECT * FROM sys.objects WHERE name = 'stand_subdivisions' AND type = 'U')
    DROP TABLE stand_subdivisions;
IF EXISTS (SELECT * FROM sys.objects WHERE name = 'stand_survey' AND type = 'U')
    DROP TABLE stand_survey;
IF EXISTS (SELECT * FROM sys.objects WHERE name = 'stands' AND type = 'U')
    DROP TABLE stands;
IF EXISTS (SELECT * FROM sys.objects WHERE name = 'metadata_catalogue' AND type = 'U')
    DROP TABLE metadata_catalogue;
GO

IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_allocated_stands')
    DROP VIEW vw_allocated_stands;
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_owner_portfolio')
    DROP VIEW vw_owner_portfolio;
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_disability_summary')
    DROP VIEW vw_disability_summary;
GO

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_allocate_stand')
    DROP PROCEDURE sp_allocate_stand;
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_owner_report')
    DROP PROCEDURE sp_owner_report;
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_available_subdivisions')
    DROP PROCEDURE sp_available_subdivisions;
GO


-- ═══════════════════════════════════════════════════════
--  1. TABLE CREATIONS & CONSTRAINTS (GEOGRAPHY GPS)
-- ═══════════════════════════════════════════════════════

-- Note: Transparent Data Encryption (TDE) comment as requested by Q6:
-- To enable TDE on MS SQL:
-- CREATE MASTER KEY ENCRYPTION BY PASSWORD = 'MasterPassword123!';
-- CREATE CERTIFICATE TDECert WITH SUBJECT = 'TDE Certificate';
-- CREATE DATABASE ENCRYPTION KEY WITH ALGORITHM = AES_256 ENCRYPTION BY SERVER CERTIFICATE TDECert;
-- ALTER DATABASE devdb SET ENCRYPTION ON;

-- Entity 1: stands
CREATE TABLE stands (
    stand_number VARCHAR(20) NOT NULL PRIMARY KEY,
    location VARCHAR(200) NOT NULL,
    size_m2 DECIMAL(12,2) NOT NULL,
    activity VARCHAR(50) NOT NULL,
    picture_url VARCHAR(500) NULL,
    gps_coordinates GEOGRAPHY NOT NULL, -- MS SQL Geography GPS Type
    location_city VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    CONSTRAINT chk_stands_size CHECK (size_m2 > 0),
    CONSTRAINT chk_stands_activity CHECK (activity IN ('Residential', 'Commercial'))
);
GO

-- Entity 2: stand_survey
CREATE TABLE stand_survey (
    survey_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    stand_number VARCHAR(20) NOT NULL,
    survey_status BIT NOT NULL DEFAULT 0,
    province VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    CONSTRAINT fk_survey_stand FOREIGN KEY (stand_number) 
        REFERENCES stands (stand_number) ON DELETE CASCADE ON UPDATE CASCADE
);
GO

-- Entity 3: stand_subdivisions
CREATE TABLE stand_subdivisions (
    subdivision_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    stand_number VARCHAR(20) NOT NULL,
    allocation_status BIT NOT NULL DEFAULT 0,
    size_m2 DECIMAL(10,2) NOT NULL,
    remarks NVARCHAR(MAX) NULL,
    created_at DATETIME DEFAULT GETDATE(),
    CONSTRAINT fk_subdivisions_stand FOREIGN KEY (stand_number) 
        REFERENCES stands (stand_number) ON DELETE NO ACTION ON UPDATE CASCADE,
    CONSTRAINT chk_subdivision_size CHECK (size_m2 > 0)
);
GO

-- Entity 4: stand_owners
CREATE TABLE stand_owners (
    stand_owner_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    firstname VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(10) NOT NULL,
    disability_status BIT NOT NULL DEFAULT 0,
    province VARCHAR(100) NOT NULL,
    district VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    CONSTRAINT chk_owners_gender CHECK (gender IN ('Male', 'Female', 'Other'))
);
GO

-- Entity 5: dependents
CREATE TABLE dependents (
    dependent_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    stand_owner_id INT NOT NULL,
    firstname VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(10) NOT NULL,
    disability_status BIT NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE(),
    CONSTRAINT fk_dependents_owner FOREIGN KEY (stand_owner_id) 
        REFERENCES stand_owners (stand_owner_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_dependents_gender CHECK (gender IN ('Male', 'Female', 'Other'))
);
GO

-- Entity 6: stand_allocations
CREATE TABLE stand_allocations (
    allocation_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    stand_owner_id INT NOT NULL,
    subdivision_id INT NOT NULL,
    date_of_allocation DATE NOT NULL,
    price_per_m2 DECIMAL(10,2) NOT NULL,
    created_at DATETIME DEFAULT GETDATE(),
    CONSTRAINT fk_allocations_owner FOREIGN KEY (stand_owner_id) 
        REFERENCES stand_owners (stand_owner_id) ON DELETE NO ACTION ON UPDATE CASCADE,
    CONSTRAINT fk_allocations_subdivision FOREIGN KEY (subdivision_id) 
        REFERENCES stand_subdivisions (subdivision_id) ON DELETE NO ACTION ON UPDATE CASCADE,
    CONSTRAINT chk_allocations_price CHECK (price_per_m2 > 0)
);
GO

-- Audit Table
CREATE TABLE stand_allocations_audit (
    audit_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    action_type VARCHAR(10) NOT NULL,
    allocation_id INT NOT NULL,
    stand_owner_id INT NOT NULL,
    subdivision_id INT NOT NULL,
    date_of_allocation DATE NOT NULL,
    price_per_m2 DECIMAL(10,2) NOT NULL,
    changed_by VARCHAR(100) NOT NULL,
    changed_at DATETIME DEFAULT GETDATE()
);
GO

-- Metadata Catalog Table
CREATE TABLE metadata_catalogue (
    table_name VARCHAR(100) NOT NULL,
    column_name VARCHAR(100) NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    is_pii BIT DEFAULT 0,
    data_classification VARCHAR(50) DEFAULT 'Internal',
    data_owner VARCHAR(100) DEFAULT 'Ministry of Lands',
    data_steward VARCHAR(100) DEFAULT 'GIS Department',
    PRIMARY KEY (table_name, column_name)
);
GO


-- ═══════════════════════════════════════════════════════
--  2. VIEWS CREATION
-- ═══════════════════════════════════════════════════════

CREATE VIEW vw_allocated_stands AS
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
GO

CREATE VIEW vw_owner_portfolio AS
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
GO

CREATE VIEW vw_disability_summary AS
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
    WHERE disability_status = 1 
    GROUP BY province
) owner_stats ON p.province = owner_stats.province
LEFT JOIN (
    SELECT so.province, COUNT(*) AS disabled_dependents_count
    FROM dependents d
    JOIN stand_owners so ON d.stand_owner_id = so.stand_owner_id
    WHERE d.disability_status = 1
    GROUP BY so.province
) dep_stats ON p.province = dep_stats.province;
GO


-- ═══════════════════════════════════════════════════════
--  3. TRIGGERS CREATION
-- ═══════════════════════════════════════════════════════

-- Trigger 1: Auditing allocations
CREATE TRIGGER trg_audit_allocations ON stand_allocations
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    IF EXISTS(SELECT * FROM inserted) AND EXISTS(SELECT * FROM deleted) -- UPDATE
    BEGIN
        INSERT INTO stand_allocations_audit (action_type, allocation_id, stand_owner_id, subdivision_id, date_of_allocation, price_per_m2, changed_by)
        SELECT 'UPDATE', allocation_id, stand_owner_id, subdivision_id, date_of_allocation, price_per_m2, SYSTEM_USER FROM inserted;
    END
    ELSE IF EXISTS(SELECT * FROM inserted) -- INSERT
    BEGIN
        INSERT INTO stand_allocations_audit (action_type, allocation_id, stand_owner_id, subdivision_id, date_of_allocation, price_per_m2, changed_by)
        SELECT 'INSERT', allocation_id, stand_owner_id, subdivision_id, date_of_allocation, price_per_m2, SYSTEM_USER FROM inserted;
    END
    ELSE IF EXISTS(SELECT * FROM deleted) -- DELETE
    BEGIN
        INSERT INTO stand_allocations_audit (action_type, allocation_id, stand_owner_id, subdivision_id, date_of_allocation, price_per_m2, changed_by)
        SELECT 'DELETE', allocation_id, stand_owner_id, subdivision_id, date_of_allocation, price_per_m2, SYSTEM_USER FROM deleted;
    END
END;
GO

-- Trigger 2: Check Subdivision Size BEFORE INSERT
CREATE TRIGGER trg_check_subdivision_size ON stand_subdivisions
INSTEAD OF INSERT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @stand_number VARCHAR(20);
    DECLARE @size_m2 DECIMAL(10,2);
    DECLARE @remarks NVARCHAR(MAX);
    
    DECLARE ins_cursor CURSOR FOR 
    SELECT stand_number, size_m2, remarks FROM inserted;
    
    OPEN ins_cursor;
    FETCH NEXT FROM ins_cursor INTO @stand_number, @size_m2, @remarks;
    
    WHILE @@FETCH_STATUS = 0
    BEGIN
        DECLARE @parent_size DECIMAL(12,2);
        DECLARE @current_sum DECIMAL(12,2);
        DECLARE @survey_exists INT;
        
        -- Business Rule: A stand must have an active survey status verified before subdividing.
        SELECT @survey_exists = COUNT(*) FROM stand_survey WHERE stand_number = @stand_number AND survey_status = 1;
        IF @survey_exists = 0
        BEGIN
            RAISERROR('Business Rule Violation: A stand must have an active survey status verified before subdividing.', 16, 1);
            ROLLBACK TRANSACTION;
            RETURN;
        END

        SELECT @parent_size = size_m2 FROM stands WHERE stand_number = @stand_number;
        SELECT @current_sum = COALESCE(SUM(size_m2), 0) FROM stand_subdivisions WHERE stand_number = @stand_number;
        
        IF (@current_sum + @size_m2) > @parent_size
        BEGIN
            RAISERROR('Business Rule Violation: Total subdivisions size exceeds parent stand capacity.', 16, 1);
            ROLLBACK TRANSACTION;
            RETURN;
        END
        
        INSERT INTO stand_subdivisions (stand_number, allocation_status, size_m2, remarks)
        VALUES (@stand_number, 0, @size_m2, @remarks);
        
        FETCH NEXT FROM ins_cursor INTO @stand_number, @size_m2, @remarks;
    END
    
    CLOSE ins_cursor;
    DEALLOCATE ins_cursor;
END;
GO

-- Trigger 3: Allocation Status Updates
CREATE TRIGGER trg_allocation_status_ins ON stand_allocations
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE sub 
    SET sub.allocation_status = 1
    FROM stand_subdivisions sub
    JOIN inserted i ON sub.subdivision_id = i.subdivision_id;
END;
GO

CREATE TRIGGER trg_allocation_status_del ON stand_allocations
AFTER DELETE
AS
BEGIN
    SET NOCOUNT ON;
    UPDATE sub 
    SET sub.allocation_status = 0
    FROM stand_subdivisions sub
    JOIN deleted d ON sub.subdivision_id = d.subdivision_id;
END;
GO


-- ═══════════════════════════════════════════════════════
--  4. STORED PROCEDURES
-- ═══════════════════════════════════════════════════════

-- Proc 1: Allocation Transaction Manager
CREATE PROCEDURE sp_allocate_stand
    @owner_id INT,
    @subdivision_id INT,
    @price_per_m2 DECIMAL(10,2)
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @already_allocated BIT;
    DECLARE @is_owner_valid INT;
    DECLARE @is_sub_valid INT;
    
    BEGIN TRANSACTION;
    
    BEGIN TRY
        -- Check Owner
        SELECT @is_owner_valid = COUNT(*) FROM stand_owners WHERE stand_owner_id = @owner_id;
        IF @is_owner_valid = 0
        BEGIN
            RAISERROR('Validation Error: Owner ID is not registered.', 16, 1);
        END
        
        -- Check Subdivision
        SELECT @is_sub_valid = COUNT(*) FROM stand_subdivisions WHERE subdivision_id = @subdivision_id;
        IF @is_sub_valid = 0
        BEGIN
            RAISERROR('Validation Error: Subdivision ID does not exist.', 16, 1);
        END
        
        -- Price Check
        IF @price_per_m2 <= 0
        BEGIN
            RAISERROR('Validation Error: Price per m2 must be positive.', 16, 1);
        END
        
        -- Verify status
        SELECT @already_allocated = allocation_status FROM stand_subdivisions WHERE subdivision_id = @subdivision_id;
        IF @already_allocated = 1
        BEGIN
            RAISERROR('Business Rule Violation: This subdivision is already allocated.', 16, 1);
        END
        
        -- Insert allocation record
        INSERT INTO stand_allocations (stand_owner_id, subdivision_id, date_of_allocation, price_per_m2)
        VALUES (@owner_id, @subdivision_id, CAST(GETDATE() AS DATE), @price_per_m2);
        
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
        BEGIN
            ROLLBACK TRANSACTION;
        END
        THROW;
    END CATCH
END;
GO

-- Proc 2: Owner Portfolio Report
CREATE PROCEDURE sp_owner_report
    @owner_id INT
AS
BEGIN
    SET NOCOUNT ON;
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
    WHERE so.stand_owner_id = @owner_id;
END;
GO

-- Proc 3: Available subdivisions
CREATE PROCEDURE sp_available_subdivisions
    @province VARCHAR(100),
    @district VARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;
    SELECT 
        sub.subdivision_id,
        sub.stand_number,
        sub.size_m2,
        sub.remarks,
        sur.province,
        sur.district
    FROM stand_subdivisions sub
    JOIN stand_survey sur ON sub.stand_number = sur.stand_number
    WHERE sub.allocation_status = 0
      AND sur.province = @province
      AND sur.district = @district;
END;
GO


-- ═══════════════════════════════════════════════════════
--  5. OPTIMISATIONS & INDEXING (FILTERED INDEX)
-- ═══════════════════════════════════════════════════════

-- 1. Composite Index on Geography Location search
CREATE INDEX idx_survey_mssql_loc ON stand_survey (province, district);
CREATE INDEX idx_owners_mssql_loc ON stand_owners (province, district);
GO

-- 2. Filtered Index on unallocated subdivisions (Q7 Requirement)
CREATE INDEX idx_subdivisions_filtered_unallocated 
ON stand_subdivisions (subdivision_id, size_m2) 
WHERE allocation_status = 0;
GO

-- 3. Geography index on stands boundary
CREATE SPATIAL INDEX idx_stands_spatial_mssql ON stands(gps_coordinates);
GO


-- ═══════════════════════════════════════════════════════
--  6. SECURITY MEASURES (ROW-LEVEL SECURITY)
-- ═══════════════════════════════════════════════════════

-- Inline Security Predicate Function (Q6 Row Level Security)
CREATE FUNCTION dbo.fn_securitypredicate(@OwnerID INT)
RETURNS TABLE
WITH SCHEMABINDING
AS
RETURN SELECT 1 AS fn_securitypredicate_result
WHERE 
    CAST(SESSION_CONTEXT(N'current_user_role') AS VARCHAR(100)) = 'land_admin'
    OR CAST(SESSION_CONTEXT(N'current_user_role') AS VARCHAR(100)) = 'land_app'
    OR @OwnerID = CAST(SESSION_CONTEXT(N'current_owner_id') AS INT);
GO

-- Create Security Policy applying Filter Predicate
CREATE SECURITY POLICY OwnerFilter
ADD FILTER PREDICATE dbo.fn_securitypredicate(stand_owner_id)
ON dbo.stand_owners
WITH (STATE = ON);
GO

-- Role Creation and grants (commented for init context)
-- CREATE ROLE land_readonly;
-- GRANT SELECT ON OBJECT::vw_allocated_stands TO land_readonly;
-- ...
-- CREATE ROLE land_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE TO land_app;


-- ═══════════════════════════════════════════════════════
--  7. SEED DATA GENERATION (ZIMBABWE PLACE NAMES)
-- ═══════════════════════════════════════════════════════

INSERT INTO stands (stand_number, location, size_m2, activity, picture_url, gps_coordinates, location_city) VALUES
('STD-HAR-001', 'Borrowdale Brooke Golf Estate, Section A', 4000.00, 'Residential', 'http://images.lands.gov.zw/stands/std-har-001.png', geography::STGeomFromText('POLYGON((31.111 -17.722, 31.115 -17.722, 31.115 -17.726, 31.111 -17.726, 31.111 -17.722))', 4326), 'Harare'),
('STD-BUL-002', 'Suburbs Road Near Ascot Mall', 3000.00, 'Residential', 'http://images.lands.gov.zw/stands/std-bul-002.png', geography::STGeomFromText('POLYGON((28.601 -20.155, 28.605 -20.155, 28.605 -20.159, 28.601 -20.159, 28.601 -20.155))', 4326), 'Bulawayo'),
('STD-MUT-003', 'Chitepo Main Street Boulevard Commercial Hub', 7500.00, 'Commercial', 'http://images.lands.gov.zw/stands/std-mut-003.png', geography::STGeomFromText('POLYGON((32.668 -18.971, 32.674 -18.971, 32.674 -18.976, 32.668 -18.976, 32.668 -18.971))', 4326), 'Mutare'),
('STD-GWE-004', 'Senga Industrial Area Main Bypass', 12000.00, 'Commercial', 'http://images.lands.gov.zw/stands/std-gwe-004.png', geography::STGeomFromText('POLYGON((29.831 -19.461, 29.841 -19.461, 29.841 -19.469, 29.831 -19.469, 29.831 -19.461))', 4326), 'Gweru'),
('STD-MAS-005', 'Rhodene High-density Layout Block D', 2500.00, 'Residential', 'http://images.lands.gov.zw/stands/std-mas-005.png', geography::STGeomFromText('POLYGON((30.825 -20.065, 30.829 -20.065, 30.829 -20.069, 30.825 -20.069, 30.825 -20.065))', 4326), 'Masvingo');

INSERT INTO stand_survey (stand_number, survey_status, province, district) VALUES
('STD-HAR-001', 1, 'Harare', 'Harare Central'),
('STD-BUL-002', 1, 'Bulawayo', 'Bulawayo Central'),
('STD-MUT-003', 1, 'Manicaland', 'Mutare'),
('STD-GWE-004', 1, 'Midlands', 'Gweru'),
('STD-MAS-005', 1, 'Masvingo', 'Masvingo');

-- Insert subdivisions using standard INSERT (which triggers INSTEAD OF trigger)
INSERT INTO stand_subdivisions (stand_number, size_m2, remarks) VALUES
('STD-HAR-001', 1500.00, 'Divided Brooke plot East Wing'),
('STD-HAR-001', 2000.00, 'Divided Brooke plot West Wing'),
('STD-BUL-002', 1200.00, 'Ascot subdiv Sector 1'),
('STD-BUL-002', 1500.00, 'Ascot subdiv Sector 2'),
('STD-MUT-003', 3500.00, 'Commercial plaza division North'),
('STD-MUT-003', 3000.00, 'Commercial plaza division South'),
('STD-GWE-004', 6000.00, 'Senga Heavy Yard Subdivision A'),
('STD-MAS-005', 1000.00, 'Rhodene Corner Lot A'),
('STD-MAS-005', 1200.00, 'Rhodene Corner Lot B');

INSERT INTO stand_owners (firstname, date_of_birth, gender, disability_status, province, district) VALUES
('Tendai Mupfumi', '1980-04-12', 'Male', 0, 'Harare', 'Harare Central'),
('Chipo Sibanda', '1988-11-23', 'Female', 1, 'Bulawayo', 'Bulawayo Central'),
('Farai Mutasa', '1975-06-30', 'Male', 0, 'Manicaland', 'Mutare'),
('Nyarai Zhou', '1992-01-15', 'Female', 0, 'Midlands', 'Gweru'),
('Tinashe Moyo', '1982-08-05', 'Male', 1, 'Masvingo', 'Masvingo');

INSERT INTO dependents (stand_owner_id, firstname, date_of_birth, gender, disability_status) VALUES
(1, 'Rufaro Mupfumi', '2010-05-14', 'Female', 0),
(1, 'Kundai Mupfumi', '2015-09-20', 'Male', 0),
(2, 'Lindiwe Sibanda', '2012-03-04', 'Female', 1),
(3, 'Tariro Mutasa', '2008-07-22', 'Female', 0),
(5, 'Tatenda Moyo', '2014-12-01', 'Male', 0);

-- Allocate subdivisions using transaction Proc
EXEC sp_allocate_stand 1, 1, 150.00;
EXEC sp_allocate_stand 2, 3, 120.00;
EXEC sp_allocate_stand 3, 5, 200.00;
EXEC sp_allocate_stand 4, 7, 85.00;
EXEC sp_allocate_stand 5, 8, 110.00;

-- Populate Data Catalogue Table manually for compliance
INSERT INTO metadata_catalogue (table_name, column_name, data_type, is_pii, data_classification) VALUES
('stands', 'stand_number', 'VARCHAR', 0, 'Public'),
('stands', 'gps_coordinates', 'GEOGRAPHY', 0, 'Internal'),
('stand_owners', 'firstname', 'VARCHAR', 1, 'Confidential'),
('stand_owners', 'date_of_birth', 'DATE', 1, 'Confidential'),
('stand_owners', 'gender', 'VARCHAR', 1, 'Confidential'),
('stand_owners', 'disability_status', 'BIT', 1, 'Confidential'),
('dependents', 'firstname', 'VARCHAR', 1, 'Confidential'),
('dependents', 'date_of_birth', 'DATE', 1, 'Confidential');
GO
