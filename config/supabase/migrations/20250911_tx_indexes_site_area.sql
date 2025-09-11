-- Enable trigram search if not present
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Add normalized site areas for filtering/analytics
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS site_area_acres NUMERIC(12,4);
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS site_area_sqft NUMERIC(12,2);

-- Helpful indexes for dashboard/search
CREATE INDEX IF NOT EXISTS idx_transactions_tx_date ON transactions (transaction_date DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_price ON transactions (price);
CREATE INDEX IF NOT EXISTS idx_transactions_buyer_name ON transactions (LOWER(buyer_name));
CREATE INDEX IF NOT EXISTS idx_transactions_seller_name ON transactions (LOWER(seller_name));

-- Trigram indexes to speed up ILIKE / partial searches
CREATE INDEX IF NOT EXISTS trgm_transactions_buyer ON transactions USING GIN (buyer_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS trgm_transactions_seller ON transactions USING GIN (seller_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS trgm_transactions_address_raw ON transactions USING GIN (address_raw gin_trgm_ops);

