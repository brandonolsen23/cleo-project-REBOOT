-- Migration: add Realtrack coverage columns to properties and transactions

-- Properties
ALTER TABLE properties ADD COLUMN IF NOT EXISTS arn TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS pin TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS alt_address1 TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS alt_address2 TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS alt_address3 TEXT;

CREATE INDEX IF NOT EXISTS idx_properties_arn ON properties (arn);
CREATE INDEX IF NOT EXISTS idx_properties_pin ON properties (pin);

-- Transactions
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS arn TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS pin TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS address_raw TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS city_raw TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS alt_address1 TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS alt_address2 TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS alt_address3 TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS buyer_name TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS buyer_address TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS buyer_alt_name1 TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS buyer_alt_name2 TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS buyer_alt_name3 TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS buyer_contact_first_name TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS buyer_contact_last_name TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS buyer_phone TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS seller_name TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS seller_address TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS seller_alt_name1 TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS seller_alt_name2 TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS seller_alt_name3 TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS seller_contact_first_name TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS seller_contact_last_name TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS seller_phone TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS brokerage_name TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS brokerage_phone TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS site TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS relationship TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS source_url TEXT;

CREATE INDEX IF NOT EXISTS idx_transactions_arn ON transactions (arn);
CREATE INDEX IF NOT EXISTS idx_transactions_pin ON transactions (pin);
CREATE INDEX IF NOT EXISTS idx_transactions_source_url ON transactions (source_url);

