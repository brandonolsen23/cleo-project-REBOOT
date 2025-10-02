-- Migration: Allow Anonymous Read Access for Development
-- Date: 2025-10-02
-- Purpose: Allow unauthenticated users to READ business data for development
-- Security: Read-only access, writes still require authentication

-- Properties: Allow anonymous SELECT
CREATE POLICY "Allow anonymous read access to properties"
  ON public.properties
  FOR SELECT
  USING (true);

-- Transactions: Allow anonymous SELECT
CREATE POLICY "Allow anonymous read access to transactions"
  ON public.transactions
  FOR SELECT
  USING (true);

-- Brands: Allow anonymous SELECT
CREATE POLICY "Allow anonymous read access to brands"
  ON public.brands
  FOR SELECT
  USING (true);

-- Brand Locations: Allow anonymous SELECT
CREATE POLICY "Allow anonymous read access to brand_locations"
  ON public.brand_locations
  FOR SELECT
  USING (true);

-- Property Brand Links: Allow anonymous SELECT
CREATE POLICY "Allow anonymous read access to property_brand_links"
  ON public.property_brand_links
  FOR SELECT
  USING (true);

-- Owners: Allow anonymous SELECT
CREATE POLICY "Allow anonymous read access to owners"
  ON public.owners
  FOR SELECT
  USING (true);

-- Owner Properties: Allow anonymous SELECT (if table exists and has RLS)
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'owner_properties') THEN
    IF EXISTS (
      SELECT FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public' AND c.relname = 'owner_properties' AND c.relrowsecurity = true
    ) THEN
      EXECUTE 'CREATE POLICY "Allow anonymous read access to owner_properties" ON public.owner_properties FOR SELECT USING (true)';
    END IF;
  END IF;
END $$;

-- Notes: Allow anonymous SELECT
CREATE POLICY "Allow anonymous read access to notes"
  ON public.notes
  FOR SELECT
  USING (true);

-- Comments for documentation
COMMENT ON POLICY "Allow anonymous read access to properties" ON public.properties IS 'Development: Allows unauthenticated users to view properties';
COMMENT ON POLICY "Allow anonymous read access to transactions" ON public.transactions IS 'Development: Allows unauthenticated users to view transactions';
COMMENT ON POLICY "Allow anonymous read access to brands" ON public.brands IS 'Development: Allows unauthenticated users to view brands';
