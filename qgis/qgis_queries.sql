-- ═══════════════════════════════════════════════════════
--  MCS 504 DATABASE PROJECT — POSTGIS SPATIAL LAYERS FOR QGIS
-- ═══════════════════════════════════════════════════════

-- ═══════════════════════════════════════════════════════
--  LAYER 1: STAND LOCATIONS (POINT LAYER REPRESENTATION)
-- ═══════════════════════════════════════════════════════
-- QGIS consumes this query to display centroids of surveyed stands
SELECT 
    s.stand_number,
    s.location_city,
    s.activity,
    s.size_m2,
    -- Compute the spatial centroid polygon midpoint as standard Point geometry
    ST_Centroid(s.gps_coordinates) AS geom_point,
    sur.province,
    sur.district
FROM stands s
JOIN stand_survey sur ON s.stand_number = sur.stand_number;


-- ═══════════════════════════════════════════════════════
--  LAYER 2: STAND BOUNDARIES (POLYGON LAYER REPRESENTATION)
-- ═══════════════════════════════════════════════════════
-- QGIS consumes this query to display full boundary footprints
SELECT 
    s.stand_number,
    s.location AS stand_location,
    s.size_m2,
    s.activity,
    s.location_city,
    -- Polygon boundary geometry
    s.gps_coordinates AS geom_polygon
FROM stands s;


-- ═══════════════════════════════════════════════════════
--  LAYER 3: SUBDIVISIONS COLOURED BY ALLOCATION STATUS
-- ═══════════════════════════════════════════════════════
-- Shows subdivisions overlay colored by active allocation status (Yes/No)
SELECT 
    sub.subdivision_id,
    sub.stand_number,
    sub.size_m2 AS subdivision_size,
    sub.remarks,
    -- Boolean allocation status mapped to readable text
    CASE 
        WHEN sub.allocation_status = TRUE THEN 'Allocated'
        ELSE 'Available'
    END AS allocation_state,
    -- Joins parent geometry boundary for shape depiction
    s.gps_coordinates AS geom_polygon
FROM stand_subdivisions sub
JOIN stands s ON sub.stand_number = s.stand_number;
