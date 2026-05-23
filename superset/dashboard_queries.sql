-- ═══════════════════════════════════════════════════════
--  MCS 504 DATABASE PROJECT — SUPERSET DASHBOARD QUERIES
--  All queries run against PostgreSQL + PostGIS (public schema)
-- ═══════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════
--  CHART 1: STANDS BY ACTIVITY TYPE (PIE CHART)
-- ═══════════════════════════════════════════════════════
-- Displays distribution of land stands across Residential and Commercial
SELECT 
    activity AS activity_type,
    COUNT(*) AS stands_count,
    SUM(size_m2) AS total_footprint_m2
FROM stands
GROUP BY activity;


-- ═══════════════════════════════════════════════════════
--  CHART 2: ALLOCATIONS OVER TIME (LINE CHART)
-- ═══════════════════════════════════════════════════════
-- Tracks temporal assignment velocity of land allocations
SELECT 
    -- Group by month and year of allocation
    DATE_TRUNC('month', date_of_allocation) AS allocation_month,
    COUNT(*) AS allocation_count,
    SUM(sub.size_m2) AS allocated_m2,
    SUM(sub.size_m2 * sa.price_per_m2) AS total_allocation_usd
FROM stand_allocations sa
JOIN stand_subdivisions sub ON sa.subdivision_id = sub.subdivision_id
GROUP BY DATE_TRUNC('month', date_of_allocation)
ORDER BY allocation_month ASC;


-- ═══════════════════════════════════════════════════════
--  CHART 3: OWNERS BY PROVINCE (BAR CHART)
-- ═══════════════════════════════════════════════════════
-- Displays spatial demographic spread of registered owners
SELECT 
    province,
    COUNT(*) AS total_owners,
    SUM(CASE WHEN gender = 'Male' THEN 1 ELSE 0 END) AS male_owners,
    SUM(CASE WHEN gender = 'Female' THEN 1 ELSE 0 END) AS female_owners
FROM stand_owners
GROUP BY province
ORDER BY total_owners DESC;


-- ═══════════════════════════════════════════════════════
--  CHART 4: DISABILITY RATIO IN OWNERS & DEPENDENTS (DONUT CHART)
-- ═══════════════════════════════════════════════════════
-- Tracks the ratio of priority assistance allocations versus standard listings
SELECT 
    'Owners - Disability Priority Assisted' AS category,
    COUNT(*) AS count
FROM stand_owners
WHERE disability_status = TRUE

UNION ALL

SELECT 
    'Owners - Standard Allotment' AS category,
    COUNT(*) AS count
FROM stand_owners
WHERE disability_status = FALSE

UNION ALL

SELECT 
    'Dependents - Disability Priority Assisted' AS category,
    COUNT(*) AS count
FROM dependents
WHERE disability_status = TRUE

UNION ALL

SELECT 
    'Dependents - Standard' AS category,
    COUNT(*) AS count
FROM dependents
WHERE disability_status = FALSE;
