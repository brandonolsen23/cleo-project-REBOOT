-- Add unique constraint to nar_address_cache for cache key
-- This allows ON CONFLICT upserts when saving to cache

-- Create unique index on cache key
CREATE UNIQUE INDEX IF NOT EXISTS idx_nar_cache_unique_key
    ON nar_address_cache(
        address_normalized,
        COALESCE(city_hint, ''),
        COALESCE(postal_code, '')
    );

-- Verify constraint
DO $$
BEGIN
    RAISE NOTICE '✅ Added unique constraint to nar_address_cache';
    RAISE NOTICE '   Cache keys: (address_normalized, city_hint, postal_code)';
END $$;
