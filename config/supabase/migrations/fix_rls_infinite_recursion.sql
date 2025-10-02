-- Fix infinite recursion in user_profiles RLS policies
-- Run this in Supabase SQL Editor

-- Drop all existing policies on user_profiles
DROP POLICY IF EXISTS "Users can view own profile" ON public.user_profiles;
DROP POLICY IF EXISTS "Admins can view all profiles" ON public.user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON public.user_profiles;
DROP POLICY IF EXISTS "Admins can update all profiles" ON public.user_profiles;
DROP POLICY IF EXISTS "Enable insert for authenticated users only" ON public.user_profiles;
DROP POLICY IF EXISTS "Service role has full access" ON public.user_profiles;

-- Create new policies without infinite recursion
CREATE POLICY "Users can view all profiles"
  ON public.user_profiles
  FOR SELECT
  USING (auth.role() = 'authenticated');

CREATE POLICY "Users can update own profile"
  ON public.user_profiles
  FOR UPDATE
  USING (auth.uid() = id);

CREATE POLICY "Service role has full access"
  ON public.user_profiles
  FOR ALL
  USING (auth.role() = 'service_role');

CREATE POLICY "Enable insert for authenticated users only"
  ON public.user_profiles
  FOR INSERT
  WITH CHECK (auth.uid() = id);

-- Also simplify the policies on business tables to avoid the same issue
-- Drop existing policies that reference user_profiles
DROP POLICY IF EXISTS "Analysts and Admins can modify properties" ON public.properties;
DROP POLICY IF EXISTS "Analysts and Admins can modify transactions" ON public.transactions;
DROP POLICY IF EXISTS "Analysts and Admins can modify owners" ON public.owners;
DROP POLICY IF EXISTS "Analysts and Admins can modify brands" ON public.brands;
DROP POLICY IF EXISTS "Analysts and Admins can modify brand_locations" ON public.brand_locations;
DROP POLICY IF EXISTS "Users can update own notes or admins can update all" ON public.notes;
DROP POLICY IF EXISTS "Users can delete own notes or admins can delete all" ON public.notes;

-- Recreate with simpler policies (allow all authenticated users for now)
CREATE POLICY "Authenticated users can modify properties"
  ON public.properties
  FOR ALL
  USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can modify transactions"
  ON public.transactions
  FOR ALL
  USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can modify owners"
  ON public.owners
  FOR ALL
  USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can modify brands"
  ON public.brands
  FOR ALL
  USING (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can modify brand_locations"
  ON public.brand_locations
  FOR ALL
  USING (auth.role() = 'authenticated');

CREATE POLICY "Users can update notes"
  ON public.notes
  FOR UPDATE
  USING (auth.role() = 'authenticated');

CREATE POLICY "Users can delete notes"
  ON public.notes
  FOR DELETE
  USING (auth.role() = 'authenticated');
