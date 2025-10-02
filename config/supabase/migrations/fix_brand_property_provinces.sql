-- Fix province data quality issues in properties table
-- This script safely moves misplaced data to correct fields BEFORE setting province to 'ON'
-- It does NOT delete or merge any records

-- Step 1: Move postal codes from province field to postal_code field (if postal_code is NULL)
-- Ontario postal codes start with K, L, M, N, or P
UPDATE properties
SET
  postal_code = province,
  province = 'ON'
WHERE province ~ '^[KLMNP][0-9][A-Z][0-9][A-Z][0-9]$'
  AND postal_code IS NULL;

-- Step 2: If postal code is in province but postal_code already has a value, just fix province
UPDATE properties
SET province = 'ON'
WHERE province ~ '^[KLMNP][0-9][A-Z][0-9][A-Z][0-9]$'
  AND postal_code IS NOT NULL;

-- Step 3: Move city names from province field to city field (if city is NULL)
UPDATE properties
SET
  city = CASE
    WHEN province = 'TORONTO' THEN 'Toronto'
    WHEN province = 'MISSISSAUGA' THEN 'Mississauga'
    WHEN province = 'BRAMPTON' THEN 'Brampton'
    WHEN province = 'HAMILTON' THEN 'Hamilton'
    WHEN province = 'LONDON' THEN 'London'
    WHEN province = 'MARKHAM' THEN 'Markham'
    WHEN province = 'VAUGHAN' THEN 'Vaughan'
    WHEN province = 'KITCHENER' THEN 'Kitchener'
    WHEN province = 'OAKVILLE' THEN 'Oakville'
    WHEN province = 'BURLINGTON' THEN 'Burlington'
    WHEN province = 'SCARBOROUGH' THEN 'Scarborough'
    WHEN province = 'ETOBICOKE' THEN 'Etobicoke'
    WHEN province = 'PICKERING' THEN 'Pickering'
    WHEN province = 'MILTON' THEN 'Milton'
    WHEN province = 'GEORGETOWN' THEN 'Georgetown'
    WHEN province = 'BARRIE' THEN 'Barrie'
    WHEN province = 'GLOUCESTER' THEN 'Gloucester'
    ELSE province
  END,
  province = 'ON'
WHERE province IN (
    'TORONTO', 'MISSISSAUGA', 'BRAMPTON', 'HAMILTON', 'LONDON', 'MARKHAM',
    'VAUGHAN', 'KITCHENER', 'OAKVILLE', 'BURLINGTON', 'SCARBOROUGH', 'ETOBICOKE',
    'PICKERING', 'MILTON', 'GEORGETOWN', 'BARRIE', 'GLOUCESTER'
  )
  AND city IS NULL;

-- Step 4: If city name is in province but city already has a value, just fix province
-- EXPANDED: Added all Ontario cities found in Query 5 validation
UPDATE properties
SET province = 'ON'
WHERE province IN (
    'TORONTO', 'MISSISSAUGA', 'BRAMPTON', 'HAMILTON', 'LONDON', 'MARKHAM',
    'VAUGHAN', 'KITCHENER', 'OAKVILLE', 'BURLINGTON', 'SCARBOROUGH', 'ETOBICOKE',
    'PICKERING', 'MILTON', 'GEORGETOWN', 'BARRIE', 'GLOUCESTER', 'RICHMOND',
    'NORTH', 'SAINT', 'BUILDING',
    -- Additional Ontario cities from validation
    'AJAX', 'ANCASTER', 'BELLEVILLE', 'NEPEAN', 'NIAGARA', 'NORTHBROOK',
    'ONTARIO', 'OSHAWA', 'OTTAWA', 'STOUFFVILLE', 'THORNHILL', 'WATERLOO',
    'WHITBY', 'WOODBRIDGE'
  )
  AND city IS NOT NULL;

-- Step 5: Fix properties where province is NULL but city is a known Ontario city
UPDATE properties
SET province = 'ON'
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
  );

-- Step 6: Fix any remaining properties where province = 'CA' (should be country, not province)
UPDATE properties
SET
  country = 'CA',
  province = 'ON'
WHERE province = 'CA'
  AND country IS NULL;

-- Verification query - run this after to see results
-- SELECT province, COUNT(*) as count FROM properties GROUP BY province ORDER BY count DESC;
