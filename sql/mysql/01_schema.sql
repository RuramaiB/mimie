-- ═══════════════════════════════════════════════════════
--  MCS 504 DATABASE PROJECT — MYSQL SCHEMA & OBJECTS
--  Idempotent Script: Runs on initialization
-- ═══════════════════════════════════════════════════════

SET FOREIGN_KEY_CHECKS = 0;

-- ═══════════════════════════════════════════════════════
--  DROP EXISTING OBJECTS TO ENSURE IDEMPOTENCY
-- ═══════════════════════════════════════════════════════
DROP TABLE IF EXISTS `stand_allocations_audit`;
DROP TABLE IF EXISTS `stand_allocations`;
DROP TABLE IF EXISTS `dependents`;
DROP TABLE IF EXISTS `stand_owners`;
DROP TABLE IF EXISTS `stand_subdivisions`;
DROP TABLE IF EXISTS `stand_survey`;
DROP TABLE IF EXISTS `stands`;
DROP TABLE IF EXISTS `metadata_catalogue`;

DROP VIEW IF EXISTS `vw_allocated_stands`;
DROP VIEW IF EXISTS `vw_owner_portfolio`;
DROP VIEW IF EXISTS `vw_disability_summary`;

DROP PROCEDURE IF EXISTS `sp_allocate_stand`;
DROP PROCEDURE IF EXISTS `sp_owner_report`;
DROP PROCEDURE IF EXISTS `sp_available_subdivisions`;

SET FOREIGN_KEY_CHECKS = 1;

-- ═══════════════════════════════════════════════════════
--  1. TABLE CREATIONS & CONSTRAINTS
-- ═══════════════════════════════════════════════════════

-- Entity 1: stands
CREATE TABLE `stands` (
    `stand_number` VARCHAR(20) NOT NULL COMMENT 'Primary Key: Unique identifier for land stands',
    `location` VARCHAR(200) NOT NULL COMMENT 'Address/description of stand site',
    `size_m2` DECIMAL(12,2) NOT NULL COMMENT 'Stand size in square metres',
    `activity` VARCHAR(50) NOT NULL COMMENT 'Activity type: Residential or Commercial',
    `picture_url` VARCHAR(500) NULL COMMENT 'URL/Path to physical image representation',
    `gps_coordinates` VARCHAR(500) NOT NULL COMMENT 'WGS-84 Polygon WKT boundary data',
    `location_city` VARCHAR(100) NOT NULL COMMENT 'Name of city/town',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Audit creation time',
    PRIMARY KEY (`stand_number`),
    CONSTRAINT `chk_stands_size` CHECK (`size_m2` > 0),
    CONSTRAINT `chk_stands_activity` CHECK (`activity` IN ('Residential', 'Commercial'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Core land stands catalog';

-- Entity 2: stand_survey
CREATE TABLE `stand_survey` (
    `survey_id` INT AUTO_INCREMENT NOT NULL,
    `stand_number` VARCHAR(20) NOT NULL COMMENT 'Foreign Key linking to stand details',
    `survey_status` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Indicates if survey was finalized (Yes/No)',
    `province` VARCHAR(100) NOT NULL COMMENT 'Zimbabwean Province location',
    `district` VARCHAR(100) NOT NULL COMMENT 'District of survey boundary',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`survey_id`),
    CONSTRAINT `fk_survey_stand` FOREIGN KEY (`stand_number`) 
        REFERENCES `stands` (`stand_number`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Surveys matching stands';

-- Entity 3: stand_subdivisions
CREATE TABLE `stand_subdivisions` (
    `subdivision_id` INT AUTO_INCREMENT NOT NULL,
    `stand_number` VARCHAR(20) NOT NULL COMMENT 'Foreign Key linking to main stand',
    `allocation_status` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Subdivision allocation status',
    `size_m2` DECIMAL(10,2) NOT NULL COMMENT 'Size of sub-plot in square metres',
    `remarks` TEXT NULL COMMENT 'Descriptive status comments',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`subdivision_id`),
    CONSTRAINT `fk_subdivisions_stand` FOREIGN KEY (`stand_number`) 
        REFERENCES `stands` (`stand_number`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `chk_subdivision_size` CHECK (`size_m2` > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Stand partition allotments';

-- Entity 4: stand_owners
CREATE TABLE `stand_owners` (
    `stand_owner_id` INT AUTO_INCREMENT NOT NULL,
    `firstname` VARCHAR(100) NOT NULL COMMENT 'PII: Firstname of the stand owner',
    `date_of_birth` DATE NOT NULL COMMENT 'PII: Date of birth for legal validation',
    `gender` VARCHAR(10) NOT NULL COMMENT 'PII: Gender of the holder',
    `disability_status` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'PII: Disability flag for priority assignments',
    `province` VARCHAR(100) NOT NULL COMMENT 'Owner residential province',
    `district` VARCHAR(100) NOT NULL COMMENT 'Owner residential district',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`stand_owner_id`),
    CONSTRAINT `chk_owners_gender` CHECK (`gender` IN ('Male', 'Female', 'Other'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Registered stand owners catalogue';

-- Entity 5: dependents
CREATE TABLE `dependents` (
    `dependent_id` INT AUTO_INCREMENT NOT NULL,
    `stand_owner_id` INT NOT NULL COMMENT 'Foreign Key referencing owner primary key',
    `firstname` VARCHAR(100) NOT NULL COMMENT 'PII: Dependent name',
    `date_of_birth` DATE NOT NULL COMMENT 'PII: Dependent date of birth',
    `gender` VARCHAR(10) NOT NULL COMMENT 'PII: Dependent gender',
    `disability_status` BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'PII: Dependent disability status',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`dependent_id`),
    CONSTRAINT `fk_dependents_owner` FOREIGN KEY (`stand_owner_id`) 
        REFERENCES `stand_owners` (`stand_owner_id`) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `chk_dependents_gender` CHECK (`gender` IN ('Male', 'Female', 'Other'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Owner family dependants';

-- Entity 6: stand_allocations
CREATE TABLE `stand_allocations` (
    `allocation_id` INT AUTO_INCREMENT NOT NULL,
    `stand_owner_id` INT NOT NULL COMMENT 'Foreign Key targeting stand owner',
    `subdivision_id` INT NOT NULL COMMENT 'Foreign Key targeting subdivision',
    `date_of_allocation` DATE NOT NULL COMMENT 'Date of official assignment',
    `price_per_m2` DECIMAL(10,2) NOT NULL COMMENT 'Dollar cost per square metre',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`allocation_id`),
    CONSTRAINT `fk_allocations_owner` FOREIGN KEY (`stand_owner_id`) 
        REFERENCES `stand_owners` (`stand_owner_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_allocations_subdivision` FOREIGN KEY (`subdivision_id`) 
        REFERENCES `stand_subdivisions` (`subdivision_id`) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `chk_allocations_price` CHECK (`price_per_m2` > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Many-to-Many resolved mapping linking owners to divisions';

-- Audit Table
CREATE TABLE `stand_allocations_audit` (
    `audit_id` INT AUTO_INCREMENT NOT NULL PRIMARY KEY,
    `action_type` VARCHAR(10) NOT NULL,
    `allocation_id` INT NOT NULL,
    `stand_owner_id` INT NOT NULL,
    `subdivision_id` INT NOT NULL,
    `date_of_allocation` DATE NOT NULL,
    `price_per_m2` DECIMAL(10,2) NOT NULL,
    `changed_by` VARCHAR(100) NOT NULL,
    `changed_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='History log of allocations changes';


-- ═══════════════════════════════════════════════════════
--  2. METADATA CATALOGUE TABLE & POPULATION
-- ═══════════════════════════════════════════════════════
CREATE TABLE `metadata_catalogue` (
    `table_name` VARCHAR(100) NOT NULL,
    `column_name` VARCHAR(100) NOT NULL,
    `data_type` VARCHAR(50) NOT NULL,
    `is_pii` BOOLEAN DEFAULT FALSE,
    `data_classification` VARCHAR(50) DEFAULT 'Internal',
    `data_owner` VARCHAR(100) DEFAULT 'Ministry of Lands',
    `data_steward` VARCHAR(100) DEFAULT 'GIS Department',
    PRIMARY KEY (`table_name`, `column_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Data governance classifications';


-- ═══════════════════════════════════════════════════════
--  3. VIEWS CREATION
-- ═══════════════════════════════════════════════════════

-- View 1: Allocated Stands
CREATE OR REPLACE VIEW `vw_allocated_stands` AS
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
CREATE OR REPLACE VIEW `vw_owner_portfolio` AS
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

-- View 3: Disability Summary
CREATE OR REPLACE VIEW `vw_disability_summary` AS
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


-- ═══════════════════════════════════════════════════════
--  4. TRIGGERS CREATION
-- ═══════════════════════════════════════════════════════

-- Trigger 1: Allocation Audit Log
DELIMITER //
CREATE TRIGGER `trg_audit_alloc_insert` AFTER INSERT ON `stand_allocations`
FOR EACH ROW
BEGIN
    INSERT INTO `stand_allocations_audit` 
    (`action_type`, `allocation_id`, `stand_owner_id`, `subdivision_id`, `date_of_allocation`, `price_per_m2`, `changed_by`)
    VALUES 
    ('INSERT', NEW.allocation_id, NEW.stand_owner_id, NEW.subdivision_id, NEW.date_of_allocation, NEW.price_per_m2, USER());
END //

CREATE TRIGGER `trg_audit_alloc_update` AFTER UPDATE ON `stand_allocations`
FOR EACH ROW
BEGIN
    INSERT INTO `stand_allocations_audit` 
    (`action_type`, `allocation_id`, `stand_owner_id`, `subdivision_id`, `date_of_allocation`, `price_per_m2`, `changed_by`)
    VALUES 
    ('UPDATE', NEW.allocation_id, NEW.stand_owner_id, NEW.subdivision_id, NEW.date_of_allocation, NEW.price_per_m2, USER());
END //

CREATE TRIGGER `trg_audit_alloc_delete` AFTER DELETE ON `stand_allocations`
FOR EACH ROW
BEGIN
    INSERT INTO `stand_allocations_audit` 
    (`action_type`, `allocation_id`, `stand_owner_id`, `subdivision_id`, `date_of_allocation`, `price_per_m2`, `changed_by`)
    VALUES 
    ('DELETE', OLD.allocation_id, OLD.stand_owner_id, OLD.subdivision_id, OLD.date_of_allocation, OLD.price_per_m2, USER());
END //

-- Trigger 2: Check Subdivision Size
CREATE TRIGGER `trg_check_subdivision_size` BEFORE INSERT ON `stand_subdivisions`
FOR EACH ROW
BEGIN
    DECLARE parent_size DECIMAL(12,2);
    DECLARE current_sum DECIMAL(12,2);
    DECLARE survey_exists INT;
    
    -- Check if surveyed first
    SELECT COUNT(*) INTO survey_exists FROM `stand_survey` WHERE `stand_number` = NEW.stand_number AND `survey_status` = TRUE;
    IF survey_exists = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Business Rule Violation: A stand must have an active survey status verified before subdividing.';
    END IF;

    -- Fetch stand size
    SELECT `size_m2` INTO parent_size FROM `stands` WHERE `stand_number` = NEW.stand_number;
    
    -- Sum existing subdivision sizes
    SELECT COALESCE(SUM(`size_m2`), 0) INTO current_sum 
    FROM `stand_subdivisions` 
    WHERE `stand_number` = NEW.stand_number;
    
    IF (current_sum + NEW.size_m2) > parent_size THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Business Rule Violation: Total subdivisions size exceeds parent stand capacity.';
    END IF;
END //

-- Trigger 3: Allocation Status Handler
CREATE TRIGGER `trg_allocation_status_insert` AFTER INSERT ON `stand_allocations`
FOR EACH ROW
BEGIN
    UPDATE `stand_subdivisions` 
    SET `allocation_status` = TRUE 
    WHERE `subdivision_id` = NEW.subdivision_id;
END //

CREATE TRIGGER `trg_allocation_status_delete` AFTER DELETE ON `stand_allocations`
FOR EACH ROW
BEGIN
    UPDATE `stand_subdivisions` 
    SET `allocation_status` = FALSE 
    WHERE `subdivision_id` = OLD.subdivision_id;
END //
DELIMITER ;


-- ═══════════════════════════════════════════════════════
--  5. STORED PROCEDURES
-- ═══════════════════════════════════════════════════════

DELIMITER //

-- Proc 1: Allocation Transaction Manager
CREATE PROCEDURE `sp_allocate_stand`(
    IN p_owner_id INT,
    IN p_subdivision_id INT,
    IN p_price_per_m2 DECIMAL(10,2)
)
BEGIN
    DECLARE v_already_allocated BOOLEAN;
    DECLARE v_is_owner_valid INT;
    DECLARE v_is_sub_valid INT;
    
    -- SQL rollback handling
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Transaction Rolled Back: Stand allocation failed.';
    END;

    START TRANSACTION;
    
    -- Check Owner Exists
    SELECT COUNT(*) INTO v_is_owner_valid FROM `stand_owners` WHERE `stand_owner_id` = p_owner_id;
    IF v_is_owner_valid = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Owner ID is not registered.';
    END IF;
    
    -- Check Subdivision Exists
    SELECT COUNT(*) INTO v_is_sub_valid FROM `stand_subdivisions` WHERE `subdivision_id` = p_subdivision_id;
    IF v_is_sub_valid = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Subdivision ID does not exist.';
    END IF;
    
    -- Validate Price
    IF p_price_per_m2 <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Validation Error: Price per m2 must be positive.';
    END IF;
    
    -- Verify allocation status
    SELECT `allocation_status` INTO v_already_allocated FROM `stand_subdivisions` WHERE `subdivision_id` = p_subdivision_id;
    IF v_already_allocated = TRUE THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Business Rule Violation: This subdivision is already allocated.';
    END IF;
    
    -- Add Allocation
    INSERT INTO `stand_allocations` (`stand_owner_id`, `subdivision_id`, `date_of_allocation`, `price_per_m2`)
    VALUES (p_owner_id, p_subdivision_id, CURDATE(), p_price_per_m2);
    
    COMMIT;
END //

-- Proc 2: Owner Portfolio Report
CREATE PROCEDURE `sp_owner_report`(IN p_owner_id INT)
BEGIN
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
    FROM `stand_owners` so
    LEFT JOIN `stand_allocations` sa ON so.stand_owner_id = sa.stand_owner_id
    LEFT JOIN `stand_subdivisions` sub ON sa.subdivision_id = sub.subdivision_id
    LEFT JOIN `stands` s ON sub.stand_number = s.stand_number
    WHERE so.stand_owner_id = p_owner_id;
END //

-- Proc 3: Available subdivisions listing
CREATE PROCEDURE `sp_available_subdivisions`(
    IN p_province VARCHAR(100),
    IN p_district VARCHAR(100)
)
BEGIN
    SELECT 
        sub.subdivision_id,
        sub.stand_number,
        sub.size_m2,
        sub.remarks,
        sur.province,
        sur.district
    FROM `stand_subdivisions` sub
    JOIN `stand_survey` sur ON sub.stand_number = sur.stand_number
    WHERE sub.allocation_status = FALSE
      AND sur.province = p_province
      AND sur.district = p_district;
END //

DELIMITER ;


-- ═══════════════════════════════════════════════════════
--  6. OPTIMISATIONS & INDEXING
-- ═══════════════════════════════════════════════════════

-- 1. Composite Index on Geography Location search
CREATE INDEX `idx_survey_loc` ON `stand_survey` (`province`, `district`);
CREATE INDEX `idx_owners_loc` ON `stand_owners` (`province`, `district`);

-- 2. FK references search index
CREATE INDEX `idx_subdivisions_stand` ON `stand_subdivisions` (`stand_number`);
CREATE INDEX `idx_allocations_owner` ON `stand_allocations` (`stand_owner_id`);
CREATE INDEX `idx_allocations_sub` ON `stand_allocations` (`subdivision_id`);

-- 3. Filtered Index equivalent for unallocated subdivisions (using Standard B-Tree for MySQL compatibility)
CREATE INDEX `idx_subdivisions_unallocated` ON `stand_subdivisions` (`allocation_status`, `size_m2`);


-- ═══════════════════════════════════════════════════════
--  7. DATA PROTECTION & USER SECURITIES
-- ═══════════════════════════════════════════════════════

-- Database Administrator: Full Control
CREATE USER IF NOT EXISTS 'land_admin'@'%' IDENTIFIED BY 'Admin1234!';
GRANT ALL PRIVILEGES ON `devdb`.* TO 'land_admin'@'%';

-- Application User: Executes DML and Procedures
CREATE USER IF NOT EXISTS 'land_app'@'%' IDENTIFIED BY 'AppPassword123!';
GRANT SELECT, INSERT, UPDATE, DELETE ON `devdb`.* TO 'land_app'@'%';
GRANT EXECUTE ON PROCEDURE `devdb`.`sp_allocate_stand` TO 'land_app'@'%';
GRANT EXECUTE ON PROCEDURE `devdb`.`sp_owner_report` TO 'land_app'@'%';
GRANT EXECUTE ON PROCEDURE `devdb`.`sp_available_subdivisions` TO 'land_app'@'%';

-- ReadOnly Analyst
CREATE USER IF NOT EXISTS 'land_readonly'@'%' IDENTIFIED BY 'ReadPass123!';
GRANT SELECT ON `devdb`.`vw_allocated_stands` TO 'land_readonly'@'%';
GRANT SELECT ON `devdb`.`vw_owner_portfolio` TO 'land_readonly'@'%';
GRANT SELECT ON `devdb`.`vw_disability_summary` TO 'land_readonly'@'%';
GRANT SELECT ON `devdb`.`stands` TO 'land_readonly'@'%';
GRANT SELECT ON `devdb`.`stand_survey` TO 'land_readonly'@'%';
GRANT SELECT ON `devdb`.`stand_subdivisions` TO 'land_readonly'@'%';

FLUSH PRIVILEGES;


-- ═══════════════════════════════════════════════════════
--  8. SEED DATA GENERATION (ZIMBABWE PLACE NAMES)
-- ═══════════════════════════════════════════════════════

INSERT INTO `stands` (`stand_number`, `location`, `size_m2`, `activity`, `picture_url`, `gps_coordinates`, `location_city`) VALUES
('STD-HAR-001', 'Borrowdale Brooke Golf Estate, Section A', 4000.00, 'Residential', 'http://images.lands.gov.zw/stands/std-har-001.png', 'POLYGON((31.111 -17.722, 31.115 -17.722, 31.115 -17.726, 31.111 -17.726, 31.111 -17.722))', 'Harare'),
('STD-BUL-002', 'Suburbs Road Near Ascot Mall', 3000.00, 'Residential', 'http://images.lands.gov.zw/stands/std-bul-002.png', 'POLYGON((28.601 -20.155, 28.605 -20.155, 28.605 -20.159, 28.601 -20.159, 28.601 -20.155))', 'Bulawayo'),
('STD-MUT-003', 'Chitepo Main Street Boulevard Commercial Hub', 7500.00, 'Commercial', 'http://images.lands.gov.zw/stands/std-mut-003.png', 'POLYGON((32.668 -18.971, 32.674 -18.971, 32.674 -18.976, 32.668 -18.976, 32.668 -18.971))', 'Mutare'),
('STD-GWE-004', 'Senga Industrial Area Main Bypass', 12000.00, 'Commercial', 'http://images.lands.gov.zw/stands/std-gwe-004.png', 'POLYGON((29.831 -19.461, 29.841 -19.461, 29.841 -19.469, 29.831 -19.469, 29.831 -19.461))', 'Gweru'),
('STD-MAS-005', 'Rhodene High-density Layout Block D', 2500.00, 'Residential', 'http://images.lands.gov.zw/stands/std-mas-005.png', 'POLYGON((30.825 -20.065, 30.829 -20.065, 30.829 -20.069, 30.825 -20.069, 30.825 -20.065))', 'Masvingo');

INSERT INTO `stand_survey` (`stand_number`, `survey_status`, `province`, `district`) VALUES
('STD-HAR-001', TRUE, 'Harare', 'Harare Central'),
('STD-BUL-002', TRUE, 'Bulawayo', 'Bulawayo Central'),
('STD-MUT-003', TRUE, 'Manicaland', 'Mutare'),
('STD-GWE-004', TRUE, 'Midlands', 'Gweru'),
('STD-MAS-005', TRUE, 'Masvingo', 'Masvingo');

INSERT INTO `stand_subdivisions` (`stand_number`, `allocation_status`, `size_m2`, `remarks`) VALUES
('STD-HAR-001', FALSE, 1500.00, 'Divided Brooke plot East Wing'),
('STD-HAR-001', FALSE, 2000.00, 'Divided Brooke plot West Wing'),
('STD-BUL-002', FALSE, 1200.00, 'Ascot subdiv Sector 1'),
('STD-BUL-002', FALSE, 1500.00, 'Ascot subdiv Sector 2'),
('STD-MUT-003', FALSE, 3500.00, 'Commercial plaza division North'),
('STD-MUT-003', FALSE, 3000.00, 'Commercial plaza division South'),
('STD-GWE-004', FALSE, 6000.00, 'Senga Heavy Yard Subdivision A'),
('STD-MAS-005', FALSE, 1000.00, 'Rhodene Corner Lot A'),
('STD-MAS-005', FALSE, 1200.00, 'Rhodene Corner Lot B');

INSERT INTO `stand_owners` (`firstname`, `date_of_birth`, `gender`, `disability_status`, `province`, `district`) VALUES
('Tendai Mupfumi', '1980-04-12', 'Male', FALSE, 'Harare', 'Harare Central'),
('Chipo Sibanda', '1988-11-23', 'Female', TRUE, 'Bulawayo', 'Bulawayo Central'),
('Farai Mutasa', '1975-06-30', 'Male', FALSE, 'Manicaland', 'Mutare'),
('Nyarai Zhou', '1992-01-15', 'Female', FALSE, 'Midlands', 'Gweru'),
('Tinashe Moyo', '1982-08-05', 'Male', TRUE, 'Masvingo', 'Masvingo');

INSERT INTO `dependents` (`stand_owner_id`, `firstname`, `date_of_birth`, `gender`, `disability_status`) VALUES
(1, 'Rufaro Mupfumi', '2010-05-14', 'Female', FALSE),
(1, 'Kundai Mupfumi', '2015-09-20', 'Male', FALSE),
(2, 'Lindiwe Sibanda', '2012-03-04', 'Female', TRUE),
(3, 'Tariro Mutasa', '2008-07-22', 'Female', FALSE),
(5, 'Tatenda Moyo', '2014-12-01', 'Male', FALSE);

-- Call Allocation Stored Procedures to perform safe initializations
CALL `sp_allocate_stand`(1, 1, 150.00);
CALL `sp_allocate_stand`(2, 3, 120.00);
CALL `sp_allocate_stand`(3, 5, 200.00);
CALL `sp_allocate_stand`(4, 7, 85.00);
CALL `sp_allocate_stand`(5, 8, 110.00);

-- Populate Data Catalogue Table manually for compliance
INSERT INTO `metadata_catalogue` (`table_name`, `column_name`, `data_type`, `is_pii`, `data_classification`) VALUES
('stands', 'stand_number', 'VARCHAR', FALSE, 'Public'),
('stands', 'gps_coordinates', 'VARCHAR', FALSE, 'Internal'),
('stand_owners', 'firstname', 'VARCHAR', TRUE, 'Confidential'),
('stand_owners', 'date_of_birth', 'DATE', TRUE, 'Confidential'),
('stand_owners', 'gender', 'VARCHAR', TRUE, 'Confidential'),
('stand_owners', 'disability_status', 'BOOLEAN', TRUE, 'Confidential'),
('dependents', 'firstname', 'VARCHAR', TRUE, 'Confidential'),
('dependents', 'date_of_birth', 'DATE', TRUE, 'Confidential');
