-- Cleo base schema for Supabase (PostgreSQL)
-- Safe to run multiple times (uses IF NOT EXISTS where possible)

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Utility: updated_at trigger
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- SCHEMA: public

-- Properties
CREATE TABLE IF NOT EXISTS properties (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT,
  address_line1 TEXT,
  address_line2 TEXT,
  city TEXT,
  province TEXT,
  postal_code TEXT,
  country TEXT NOT NULL DEFAULT 'CA',
  address_canonical TEXT,
  address_hash TEXT UNIQUE,
  address_hash_raw TEXT, -- pre-canonical hash computed at ingest time
  -- Parcel/registry identifiers (helpful for matching)
  arn TEXT,
  pin TEXT,
  -- Optional alternate addresses captured from sources
  alt_address1 TEXT,
  alt_address2 TEXT,
  alt_address3 TEXT,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  geocode_source TEXT,
  geocode_accuracy TEXT,
  geom GEOGRAPHY(Point, 4326),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_properties_updated_at ON properties;
CREATE TRIGGER trg_properties_updated_at
BEFORE UPDATE ON properties
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

CREATE INDEX IF NOT EXISTS idx_properties_city ON properties (city);
CREATE INDEX IF NOT EXISTS idx_properties_address_hash ON properties (address_hash);
CREATE INDEX IF NOT EXISTS idx_properties_address_hash_raw ON properties (address_hash_raw);
CREATE INDEX IF NOT EXISTS idx_properties_geom ON properties USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_properties_arn ON properties (arn);
CREATE INDEX IF NOT EXISTS idx_properties_pin ON properties (pin);

-- Owners
CREATE TABLE IF NOT EXISTS owners (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  website TEXT,
  contacts JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_owners_updated_at ON owners;
CREATE TRIGGER trg_owners_updated_at
BEFORE UPDATE ON owners
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

CREATE UNIQUE INDEX IF NOT EXISTS uq_owners_name ON owners (LOWER(name));

-- Owner to Property linkage (many-to-many, with role)
CREATE TABLE IF NOT EXISTS owner_properties (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  owner_id UUID NOT NULL REFERENCES owners(id) ON DELETE CASCADE,
  property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  role TEXT, -- e.g., 'owner', 'landlord', 'manager'
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_owner_properties ON owner_properties (owner_id, property_id, COALESCE(role,'role'));

-- Transactions
CREATE TABLE IF NOT EXISTS transactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source TEXT, -- e.g., 'realtrack'
  source_id TEXT,
  source_hash TEXT UNIQUE,
  property_id UUID REFERENCES properties(id) ON DELETE SET NULL,
  transaction_date DATE,
  transaction_type TEXT, -- e.g., 'sale', 'lease'
  price NUMERIC(18,2),
  -- Realtrack-specific mapped fields
  arn TEXT,
  pin TEXT,
  address_raw TEXT,
  city_raw TEXT,
  address_hash_raw TEXT,
  address_canonical TEXT,
  address_hash TEXT,
  alt_address1 TEXT,
  alt_address2 TEXT,
  alt_address3 TEXT,
  buyer_name TEXT,
  buyer_address TEXT,
  buyer_alt_name1 TEXT,
  buyer_alt_name2 TEXT,
  buyer_alt_name3 TEXT,
  buyer_contact_first_name TEXT,
  buyer_contact_last_name TEXT,
  buyer_phone TEXT,
  seller_name TEXT,
  seller_address TEXT,
  seller_alt_name1 TEXT,
  seller_alt_name2 TEXT,
  seller_alt_name3 TEXT,
  seller_contact_first_name TEXT,
  seller_contact_last_name TEXT,
  seller_phone TEXT,
  brokerage_name TEXT,
  brokerage_phone TEXT,
  site TEXT, -- e.g., '0.30 acre' (normalize later)
  site_area_acres NUMERIC(12,4),
  site_area_sqft NUMERIC(12,2),
  relationship TEXT,
  description TEXT,
  source_url TEXT,
  details JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_transactions_updated_at ON transactions;
CREATE TRIGGER trg_transactions_updated_at
BEFORE UPDATE ON transactions
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

CREATE INDEX IF NOT EXISTS idx_transactions_property_date ON transactions (property_id, transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_arn ON transactions (arn);
CREATE INDEX IF NOT EXISTS idx_transactions_pin ON transactions (pin);
CREATE INDEX IF NOT EXISTS idx_transactions_source_url ON transactions (source_url);
CREATE INDEX IF NOT EXISTS idx_transactions_address_hash ON transactions (address_hash);
CREATE INDEX IF NOT EXISTS idx_transactions_address_hash_raw ON transactions (address_hash_raw);

-- External identifiers mapped to properties (ARN, PIN, etc.)
CREATE TABLE IF NOT EXISTS property_identifiers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  id_type TEXT NOT NULL, -- 'ARN' | 'PIN' | 'OTHER'
  id_value TEXT NOT NULL,
  source TEXT, -- e.g., 'realtrack'
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_property_identifiers_pair_idx ON property_identifiers (id_type, id_value);
CREATE INDEX IF NOT EXISTS idx_property_identifiers_property ON property_identifiers (property_id);

-- Staging for transaction ingestion
CREATE TABLE IF NOT EXISTS stg_transactions (
  id BIGSERIAL PRIMARY KEY,
  source TEXT NOT NULL,
  source_hash TEXT NOT NULL UNIQUE,
  raw JSONB NOT NULL,
  processed BOOLEAN NOT NULL DEFAULT FALSE,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Brands
CREATE TABLE IF NOT EXISTS brands (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  website TEXT,
  meta JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_brands_updated_at ON brands;
CREATE TRIGGER trg_brands_updated_at
BEFORE UPDATE ON brands
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

CREATE UNIQUE INDEX IF NOT EXISTS uq_brands_name ON brands (LOWER(name));

-- Brand Locations
CREATE TABLE IF NOT EXISTS brand_locations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name TEXT,
  address_line1 TEXT,
  address_line2 TEXT,
  city TEXT,
  province TEXT,
  postal_code TEXT,
  country TEXT NOT NULL DEFAULT 'CA',
  address_canonical TEXT,
  address_hash TEXT,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  geocode_source TEXT,
  geocode_accuracy TEXT,
  geom GEOGRAPHY(Point, 4326),
  property_id UUID REFERENCES properties(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DROP TRIGGER IF EXISTS trg_brand_locations_updated_at ON brand_locations;
CREATE TRIGGER trg_brand_locations_updated_at
BEFORE UPDATE ON brand_locations
FOR EACH ROW EXECUTE PROCEDURE set_updated_at();

CREATE INDEX IF NOT EXISTS idx_brand_locations_brand ON brand_locations (brand_id);
CREATE INDEX IF NOT EXISTS idx_brand_locations_address_hash ON brand_locations (address_hash);
CREATE INDEX IF NOT EXISTS idx_brand_locations_geom ON brand_locations USING GIST (geom);

-- Linkage table for property-brand matches
CREATE TABLE IF NOT EXISTS property_brand_links (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  brand_location_id UUID REFERENCES brand_locations(id) ON DELETE SET NULL,
  match_method TEXT, -- 'address_hash' | 'proximity' | 'manual'
  match_score NUMERIC(5,2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_property_brand ON property_brand_links (property_id, brand_id, COALESCE(brand_location_id, '00000000-0000-0000-0000-000000000000'));

-- Notes (generic, for entities)
CREATE TABLE IF NOT EXISTS notes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  entity_type TEXT NOT NULL CHECK (entity_type IN ('property','transaction','brand','owner')),
  entity_id UUID NOT NULL,
  author TEXT,
  body TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notes_entity ON notes (entity_type, entity_id);

-- Example materialized view for quick UI fetches
CREATE MATERIALIZED VIEW IF NOT EXISTS latest_tx_per_property AS
SELECT DISTINCT ON (t.property_id)
  t.property_id,
  t.id as transaction_id,
  t.transaction_date,
  t.price,
  t.transaction_type
FROM transactions t
WHERE t.property_id IS NOT NULL
ORDER BY t.property_id, t.transaction_date DESC, t.created_at DESC;

-- Comments for documentation
COMMENT ON TABLE properties IS 'Master list of properties (retail/industrial) with canonical address and geocoding.';
COMMENT ON TABLE transactions IS 'Normalized transactions with idempotent source_hash; linkable to properties.';
COMMENT ON TABLE stg_transactions IS 'Raw ingest staging for transactions before normalization.';
COMMENT ON TABLE brands IS 'Retail brands to be scraped/managed.';
COMMENT ON TABLE brand_locations IS 'Store locations for brands; matched to properties when possible.';
COMMENT ON TABLE property_brand_links IS 'Join table with provenance of property-brand match.';
COMMENT ON TABLE owners IS 'Property owners and related data.';
COMMENT ON TABLE owner_properties IS 'Owner to property mapping with role.';
COMMENT ON TABLE notes IS 'Freeform notes attached to core entities for deal tracking.';
