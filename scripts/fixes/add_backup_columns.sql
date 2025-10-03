-- Phase 1: Add Backup Columns (Safety First)
-- This script creates backup columns to preserve original data before any fixes
-- Date: 2025-10-03

-- 1. Backup city field in properties table
ALTER TABLE properties ADD COLUMN IF NOT EXISTS city_backup TEXT;
UPDATE properties SET city_backup = city WHERE city_backup IS NULL;

-- 2. Backup city_raw field in transactions table
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS city_raw_backup TEXT;
UPDATE transactions SET city_raw_backup = city_raw WHERE city_raw_backup IS NULL;

-- 3. Verify backups were created
SELECT
    'properties' as table_name,
    COUNT(*) as total_rows,
    COUNT(city) as city_count,
    COUNT(city_backup) as backup_count,
    COUNT(*) FILTER (WHERE city IS NOT NULL AND city_backup IS NOT NULL) as both_populated
FROM properties
UNION ALL
SELECT
    'transactions' as table_name,
    COUNT(*) as total_rows,
    COUNT(city_raw) as city_count,
    COUNT(city_raw_backup) as backup_count,
    COUNT(*) FILTER (WHERE city_raw IS NOT NULL AND city_raw_backup IS NOT NULL) as both_populated
FROM transactions;
