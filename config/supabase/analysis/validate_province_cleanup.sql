-- VALIDATION QUERIES - Run these BEFORE the cleanup to verify the plan
-- DO NOT run the cleanup migration until we review these results

-- Query 1: Count records that will be affected by each step
SELECT
    'Step 1: Postal codes in province (postal_code IS NULL)' as step,
    COUNT(*) as affected_records
FROM properties
WHERE province ~ '^[KLMNP][0-9][A-Z][0-9][A-Z][0-9]$'
  AND postal_code IS NULL

UNION ALL

SELECT
    'Step 2: Postal codes in province (postal_code NOT NULL)',
    COUNT(*)
FROM properties
WHERE province ~ '^[KLMNP][0-9][A-Z][0-9][A-Z][0-9]$'
  AND postal_code IS NOT NULL

UNION ALL

SELECT
    'Step 3: City names in province (city IS NULL)',
    COUNT(*)
FROM properties
WHERE province IN (
    'TORONTO', 'MISSISSAUGA', 'BRAMPTON', 'HAMILTON', 'LONDON', 'MARKHAM',
    'VAUGHAN', 'KITCHENER', 'OAKVILLE', 'BURLINGTON', 'SCARBOROUGH', 'ETOBICOKE',
    'PICKERING', 'MILTON', 'GEORGETOWN', 'BARRIE', 'GLOUCESTER'
  )
  AND city IS NULL

UNION ALL

SELECT
    'Step 4: City names in province (city NOT NULL)',
    COUNT(*)
FROM properties
WHERE province IN (
    'TORONTO', 'MISSISSAUGA', 'BRAMPTON', 'HAMILTON', 'LONDON', 'MARKHAM',
    'VAUGHAN', 'KITCHENER', 'OAKVILLE', 'BURLINGTON', 'SCARBOROUGH', 'ETOBICOKE',
    'PICKERING', 'MILTON', 'GEORGETOWN', 'BARRIE', 'GLOUCESTER', 'RICHMOND',
    'NORTH', 'SAINT', 'BUILDING'
  )
  AND city IS NOT NULL

UNION ALL

SELECT
    'Step 5: NULL province with known ON city',
    COUNT(*)
FROM properties
WHERE province IS NULL
  AND city IN (
    'Toronto', 'Mississauga', 'Brampton', 'Hamilton', 'London', 'Markham',
    'Vaughan', 'Kitchener', 'Windsor', 'Richmond Hill', 'Oakville', 'Burlington',
    'Greater Sudbury', 'Oshawa', 'Barrie', 'St. Catharines', 'Cambridge',
    'Waterloo', 'Guelph', 'Kingston', 'Whitby', 'Ajax', 'Thunder Bay',
    'Chatham', 'Pickering', 'Niagara Falls', 'Sarnia', 'Brantford',
    'Gloucester', 'Timmins', 'York', 'Caledonia', 'Etobicoke', 'Scarborough',
    'North York', 'East York', 'Milton', 'Ottawa', 'Kanata', 'Nepean',
    'Belleville', 'Cornwall', 'Peterborough', 'Sault Ste. Marie'
  )

UNION ALL

SELECT
    'Step 6: Province = CA (country IS NULL)',
    COUNT(*)
FROM properties
WHERE province = 'CA'
  AND country IS NULL;


-- Query 2: Sample 5 records from Step 1 (postal codes → postal_code field)
SELECT
    'STEP 1 SAMPLE' as step,
    id,
    address_line1,
    city,
    province as current_province,
    postal_code as current_postal_code,
    province as will_move_to_postal_code,
    'ON' as will_set_province_to
FROM properties
WHERE province ~ '^[KLMNP][0-9][A-Z][0-9][A-Z][0-9]$'
  AND postal_code IS NULL
LIMIT 5;


-- Query 3: Sample 5 records from Step 3 (city names → city field)
SELECT
    'STEP 3 SAMPLE' as step,
    id,
    address_line1,
    city as current_city,
    province as current_province,
    CASE
        WHEN province = 'TORONTO' THEN 'Toronto'
        WHEN province = 'MISSISSAUGA' THEN 'Mississauga'
        WHEN province = 'BRAMPTON' THEN 'Brampton'
        ELSE province
    END as will_set_city_to,
    'ON' as will_set_province_to
FROM properties
WHERE province IN ('TORONTO', 'MISSISSAUGA', 'BRAMPTON', 'HAMILTON', 'LONDON', 'MARKHAM')
  AND city IS NULL
LIMIT 5;


-- Query 4: Sample 5 records from Step 5 (NULL province with known city)
SELECT
    'STEP 5 SAMPLE' as step,
    id,
    address_line1,
    city as current_city,
    province as current_province,
    'ON' as will_set_province_to
FROM properties
WHERE province IS NULL
  AND city IN ('Toronto', 'Mississauga', 'Ottawa', 'Hamilton', 'London')
LIMIT 5;


-- Query 5: Check for potential data loss - records with province values we're NOT handling
SELECT
    province,
    COUNT(*) as count,
    array_agg(DISTINCT city) FILTER (WHERE city IS NOT NULL) as sample_cities
FROM properties
WHERE province NOT IN ('ON', 'QC', 'BC', 'AB', 'MB', 'SK', 'NB', 'NS', 'PE', 'NL', 'NT', 'YT', 'NU')
  AND province IS NOT NULL
  -- Exclude the ones we're handling
  AND province !~ '^[KLMNP][0-9][A-Z][0-9][A-Z][0-9]$'  -- postal codes
  AND province NOT IN (
    'TORONTO', 'MISSISSAUGA', 'BRAMPTON', 'HAMILTON', 'LONDON', 'MARKHAM',
    'VAUGHAN', 'KITCHENER', 'OAKVILLE', 'BURLINGTON', 'SCARBOROUGH', 'ETOBICOKE',
    'PICKERING', 'MILTON', 'GEORGETOWN', 'BARRIE', 'GLOUCESTER', 'RICHMOND',
    'NORTH', 'SAINT', 'BUILDING', 'CA'
  )
GROUP BY province
ORDER BY count DESC;


-- Query 6: Simulate the final result - what will province distribution look like?
SELECT
    CASE
        -- These will all become 'ON'
        WHEN province ~ '^[KLMNP][0-9][A-Z][0-9][A-Z][0-9]$' THEN 'ON (from postal code)'
        WHEN province IN ('TORONTO', 'MISSISSAUGA', 'BRAMPTON', 'HAMILTON', 'LONDON', 'MARKHAM',
                          'VAUGHAN', 'KITCHENER', 'OAKVILLE', 'BURLINGTON', 'SCARBOROUGH', 'ETOBICOKE',
                          'PICKERING', 'MILTON', 'GEORGETOWN', 'BARRIE', 'GLOUCESTER', 'RICHMOND',
                          'NORTH', 'SAINT', 'BUILDING') THEN 'ON (from city name)'
        WHEN province IS NULL AND city IN ('Toronto', 'Mississauga', 'Brampton', 'Hamilton', 'London', 'Markham',
                                            'Ottawa', 'Windsor', 'Burlington', 'Oakville') THEN 'ON (from NULL + city)'
        WHEN province = 'CA' THEN 'ON (from CA)'
        WHEN province = 'ON' THEN 'ON (already correct)'
        ELSE province
    END as final_province,
    COUNT(*) as count
FROM properties
GROUP BY final_province
ORDER BY count DESC;
