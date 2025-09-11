# Realtrack → Cleo Schema Mapping

Source fields are preserved in `transactions` columns below and in `transactions.details` (raw JSON). Address data is also used to create/link `properties`.

## JSON Input Fields

- ARN → `transactions.arn` (also used to populate `properties.arn` when linking)
- PIN → `transactions.pin` (also used to populate `properties.pin` when linking)
- Address → `transactions.address_raw`; used to derive `properties.address_line1`
- City → `transactions.city_raw`; used to derive `properties.city`
- Raw address hash → compute from minimal normalization of `Address + City` and store in `transactions.address_hash_raw` (also populate `properties.address_hash_raw` on link/create)
- Canonical address + hash → after Phase 2 standardization, populate `transactions.address_canonical`, `transactions.address_hash` and `properties.address_canonical`, `properties.address_hash`
- AlternateAddress1/2/3 → `transactions.alt_address{1,2,3}`; may fill `properties.alt_address{1,2,3}` when applicable
- Brokerage → `transactions.brokerage_name`
- BrokeragePhone → `transactions.brokerage_phone`
- Buyer → `transactions.buyer_name`
- BuyerAddress → `transactions.buyer_address`
- BuyerAlternateName1/2/3 → `transactions.buyer_alt_name{1,2,3}`
- BuyerContactFirstName/LastName → `transactions.buyer_contact_first_name`, `transactions.buyer_contact_last_name`
- BuyerPhone → `transactions.buyer_phone`
- Seller → `transactions.seller_name`
- SellerAddress → `transactions.seller_address`
- SellerAlternateName1/2/3 → `transactions.seller_alt_name{1,2,3}`
- SellerContactFirstName/LastName → `transactions.seller_contact_first_name`, `transactions.seller_contact_last_name`
- SellerPhone → `transactions.seller_phone`
- Relationship → `transactions.relationship`
- Description → `transactions.description`
- Site → `transactions.site`
- SaleDate → `transactions.transaction_date` (parsed to DATE)
- SalePrice → `transactions.price` (parsed to NUMERIC)
- URL → `transactions.source_url`

All raw records are stored in `transactions.details` exactly as ingested.

## Property Linkage

Primary key for linkage is the address hash.

Order of operations during early ingestion (before Phase 2):
1. Compute `address_hash_raw` from `Address + City` with simple normalization (uppercase, trim, collapse spaces, strip punctuation).
2. Attempt match on `properties.address_hash_raw`.
3. If unmatched, look up by identifiers table (`property_identifiers`) using `ARN`/`PIN` when present.
4. If still unmatched, create a new `properties` row with `address_hash_raw` (leave `address_hash` NULL until Phase 2), and add identifiers to `property_identifiers`.

After Phase 2 standardization:
1. Compute canonical address + `address_hash` for transactions and properties.
2. Re-link where `address_hash` agrees and merge duplicates as needed (maintain `property_identifiers`).

## Idempotency

Compute `source_hash` as SHA-256 over a canonical string of: `ARN|PIN|Address|City|SaleDate|SalePrice`. Use `ON CONFLICT (source_hash) DO NOTHING` on insert into staging and transactions.

## Normalization Notes

- `SalePrice`: strip `$`, commas; parse to numeric.
- `SaleDate`: parse formats like `10 Apr 2025` to DATE.
- `Site`: keep text; later parse acres or square feet into normalized area fields.
- Names/phones/addresses are stored as text; later phases may normalize into party/contact tables.
