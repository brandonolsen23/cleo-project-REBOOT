-- Allow anonymous/public access to brands tables for development

-- Brands table
DROP POLICY IF EXISTS "Allow anonymous read access to brands" ON public.brands;
CREATE POLICY "Allow anonymous read access to brands"
  ON public.brands
  FOR SELECT
  USING (true);

-- Brand locations table
DROP POLICY IF EXISTS "Allow anonymous read access to brand_locations" ON public.brand_locations;
CREATE POLICY "Allow anonymous read access to brand_locations"
  ON public.brand_locations
  FOR SELECT
  USING (true);

-- Property brand links table
DROP POLICY IF EXISTS "Allow anonymous read access to property_brand_links" ON public.property_brand_links;
CREATE POLICY "Allow anonymous read access to property_brand_links"
  ON public.property_brand_links
  FOR SELECT
  USING (true);
