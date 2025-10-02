-- Migration: Allow Anonymous Read Access for Development (v2 - Safe to re-run)
-- Date: 2025-10-02
-- Purpose: Allow unauthenticated users to READ business data for development
-- Security: Read-only access, writes still require authentication

-- Drop existing policies if they exist, then recreate
-- This makes the script idempotent (safe to run multiple times)

-- Properties
DROP POLICY IF EXISTS "Allow anonymous read access to properties" ON public.properties;
CREATE POLICY "Allow anonymous read access to properties"
  ON public.properties
  FOR SELECT
  USING (true);

-- Transactions
DROP POLICY IF EXISTS "Allow anonymous read access to transactions" ON public.transactions;
CREATE POLICY "Allow anonymous read access to transactions"
  ON public.transactions
  FOR SELECT
  USING (true);

-- Brands
DROP POLICY IF EXISTS "Allow anonymous read access to brands" ON public.brands;
CREATE POLICY "Allow anonymous read access to brands"
  ON public.brands
  FOR SELECT
  USING (true);

-- Brand Locations
DROP POLICY IF EXISTS "Allow anonymous read access to brand_locations" ON public.brand_locations;
CREATE POLICY "Allow anonymous read access to brand_locations"
  ON public.brand_locations
  FOR SELECT
  USING (true);

-- Property Brand Links
DROP POLICY IF EXISTS "Allow anonymous read access to property_brand_links" ON public.property_brand_links;
CREATE POLICY "Allow anonymous read access to property_brand_links"
  ON public.property_brand_links
  FOR SELECT
  USING (true);

-- Owners
DROP POLICY IF EXISTS "Allow anonymous read access to owners" ON public.owners;
CREATE POLICY "Allow anonymous read access to owners"
  ON public.owners
  FOR SELECT
  USING (true);

-- Owner Properties (if table exists with RLS)
DO $$
BEGIN
  IF EXISTS (
    SELECT FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname = 'owner_properties' AND c.relrowsecurity = true
  ) THEN
    EXECUTE 'DROP POLICY IF EXISTS "Allow anonymous read access to owner_properties" ON public.owner_properties';
    EXECUTE 'CREATE POLICY "Allow anonymous read access to owner_properties" ON public.owner_properties FOR SELECT USING (true)';
  END IF;
END $$;

-- Notes
DROP POLICY IF EXISTS "Allow anonymous read access to notes" ON public.notes;
CREATE POLICY "Allow anonymous read access to notes"
  ON public.notes
  FOR SELECT
  USING (true);

-- Verify policies were created
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd
FROM pg_policies
WHERE policyname LIKE 'Allow anonymous read access%'
ORDER BY tablename, policyname;
