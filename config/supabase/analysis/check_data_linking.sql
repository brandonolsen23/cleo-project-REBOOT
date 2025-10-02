-- Analysis: Check if transactions are linked to properties and if brand locations are matched

-- 1. Check properties geocoding status
SELECT
    COUNT(*) as total_properties,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) as geocoded_properties,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL THEN 1 END) as not_geocoded,
    ROUND(100.0 * COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) / COUNT(*), 2) as geocoded_percentage
FROM properties
WHERE province = 'ON';

-- 2. Check transactions linking to properties
SELECT
    COUNT(*) as total_transactions,
    COUNT(property_id) as transactions_linked_to_property,
    COUNT(*) - COUNT(property_id) as transactions_not_linked,
    ROUND(100.0 * COUNT(property_id) / COUNT(*), 2) as linked_percentage
FROM transactions;

-- 3. Check transactions with addresses vs linked
SELECT
    COUNT(*) as total_transactions,
    COUNT(CASE WHEN address_raw IS NOT NULL OR address_canonical IS NOT NULL THEN 1 END) as transactions_with_address,
    COUNT(property_id) as transactions_linked_to_property,
    COUNT(CASE WHEN (address_raw IS NOT NULL OR address_canonical IS NOT NULL) AND property_id IS NULL THEN 1 END) as has_address_but_not_linked
FROM transactions;

-- 4. Check brand locations geocoding status
SELECT
    COUNT(*) as total_brand_locations,
    COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) as geocoded_brand_locations,
    COUNT(CASE WHEN latitude IS NULL OR longitude IS NULL THEN 1 END) as not_geocoded,
    ROUND(100.0 * COUNT(CASE WHEN latitude IS NOT NULL AND longitude IS NOT NULL THEN 1 END) / COUNT(*), 2) as geocoded_percentage
FROM brand_locations;

-- 5. Check brand locations linked to properties
SELECT
    COUNT(*) as total_brand_locations,
    COUNT(property_id) as brand_locations_linked_to_property,
    COUNT(*) - COUNT(property_id) as brand_locations_not_linked,
    ROUND(100.0 * COUNT(property_id) / COUNT(*), 2) as linked_percentage
FROM brand_locations;

-- 6. Check property_brand_links table
SELECT
    COUNT(*) as total_property_brand_links,
    COUNT(DISTINCT property_id) as properties_with_brands,
    COUNT(DISTINCT brand_id) as unique_brands_linked
FROM property_brand_links;

-- 7. Properties with both transactions AND brands
SELECT
    COUNT(DISTINCT p.id) as properties_with_both
FROM properties p
WHERE EXISTS (
    SELECT 1 FROM transactions t WHERE t.property_id = p.id
)
AND EXISTS (
    SELECT 1 FROM property_brand_links pbl WHERE pbl.property_id = p.id
)
AND p.province = 'ON';

-- 8. Sample of properties showing their linked data
SELECT
    p.id,
    p.address_canonical,
    p.city,
    p.latitude,
    p.longitude,
    (SELECT COUNT(*) FROM transactions t WHERE t.property_id = p.id) as transaction_count,
    (SELECT COUNT(*) FROM property_brand_links pbl WHERE pbl.property_id = p.id) as brand_count
FROM properties p
WHERE p.province = 'ON'
ORDER BY transaction_count DESC, brand_count DESC
LIMIT 10;
