-- Cleo Authentication Setup for Supabase
-- This file extends the base schema with authentication and user management

-- Enable RLS on auth schema (this is typically enabled by default in Supabase)
-- ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;

-- User profiles table
CREATE TABLE IF NOT EXISTS public.user_profiles (
  id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  email TEXT,
  full_name TEXT,
  avatar_url TEXT,
  role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('admin', 'analyst', 'viewer')),
  organization TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Enable RLS on user_profiles
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;

-- RLS Policies for user_profiles
-- Note: We use a simple policy to avoid infinite recursion
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

-- Insert policy for new user registration
CREATE POLICY "Enable insert for authenticated users only"
  ON public.user_profiles
  FOR INSERT
  WITH CHECK (auth.uid() = id);

-- Add updated_at trigger to user_profiles
DROP TRIGGER IF EXISTS trg_user_profiles_updated_at ON public.user_profiles;
CREATE TRIGGER trg_user_profiles_updated_at
  BEFORE UPDATE ON public.user_profiles
  FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

-- Function to automatically create user profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
  INSERT INTO public.user_profiles (id, email, full_name)
  VALUES (new.id, new.email, new.raw_user_meta_data->>'full_name');
  RETURN new;
END;
$$;

-- Trigger to create profile on user creation
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- Enable RLS on existing business tables
ALTER TABLE public.properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.owners ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brands ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.brand_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notes ENABLE ROW LEVEL SECURITY;

-- RLS Policies for business tables
-- Properties: Analysts and Admins can view/edit, Viewers can only view
CREATE POLICY "Authenticated users can view properties"
  ON public.properties
  FOR SELECT
  USING (auth.role() = 'authenticated');

CREATE POLICY "Analysts and Admins can modify properties"
  ON public.properties
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND role IN ('admin', 'analyst')
    )
  );

-- Transactions: Same as properties
CREATE POLICY "Authenticated users can view transactions"
  ON public.transactions
  FOR SELECT
  USING (auth.role() = 'authenticated');

CREATE POLICY "Analysts and Admins can modify transactions"
  ON public.transactions
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND role IN ('admin', 'analyst')
    )
  );

-- Owners: Same as properties
CREATE POLICY "Authenticated users can view owners"
  ON public.owners
  FOR SELECT
  USING (auth.role() = 'authenticated');

CREATE POLICY "Analysts and Admins can modify owners"
  ON public.owners
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND role IN ('admin', 'analyst')
    )
  );

-- Brands: Same as properties
CREATE POLICY "Authenticated users can view brands"
  ON public.brands
  FOR SELECT
  USING (auth.role() = 'authenticated');

CREATE POLICY "Analysts and Admins can modify brands"
  ON public.brands
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND role IN ('admin', 'analyst')
    )
  );

-- Brand locations: Same as properties
CREATE POLICY "Authenticated users can view brand_locations"
  ON public.brand_locations
  FOR SELECT
  USING (auth.role() = 'authenticated');

CREATE POLICY "Analysts and Admins can modify brand_locations"
  ON public.brand_locations
  FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND role IN ('admin', 'analyst')
    )
  );

-- Notes: Users can view all, but only create/edit their own (unless admin)
CREATE POLICY "Authenticated users can view notes"
  ON public.notes
  FOR SELECT
  USING (auth.role() = 'authenticated');

CREATE POLICY "Users can create notes"
  ON public.notes
  FOR INSERT
  WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Users can update own notes or admins can update all"
  ON public.notes
  FOR UPDATE
  USING (
    auth.uid()::text = author OR
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

CREATE POLICY "Users can delete own notes or admins can delete all"
  ON public.notes
  FOR DELETE
  USING (
    auth.uid()::text = author OR
    EXISTS (
      SELECT 1 FROM public.user_profiles
      WHERE id = auth.uid() AND role = 'admin'
    )
  );

-- Add author field to notes if it doesn't exist (should be TEXT to store user ID)
-- ALTER TABLE public.notes ALTER COLUMN author TYPE TEXT;

-- Function to get current user's role (utility for application)
CREATE OR REPLACE FUNCTION public.get_user_role()
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
DECLARE
  user_role TEXT;
BEGIN
  SELECT role INTO user_role
  FROM public.user_profiles
  WHERE id = auth.uid();

  RETURN COALESCE(user_role, 'viewer');
END;
$$;

-- Function to check if user is admin (utility for application)
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
  RETURN (
    SELECT role = 'admin'
    FROM public.user_profiles
    WHERE id = auth.uid()
  );
END;
$$;

-- Comments for documentation
COMMENT ON TABLE public.user_profiles IS 'Extended user profiles with roles and permissions';
COMMENT ON FUNCTION public.handle_new_user() IS 'Automatically creates user profile when new user signs up';
COMMENT ON FUNCTION public.get_user_role() IS 'Returns the current users role';
COMMENT ON FUNCTION public.is_admin() IS 'Returns true if current user is admin';