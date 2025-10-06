# Raw Data Analysis - Complete Pipeline Documentation

**Date:** 2025-10-03
**Purpose:** Document the ACTUAL data pipeline from raw scrapers to properties table

---

## 0. THE VERY FIRST STEP (Plain Terms)

When raw data comes from scrapers, it follows this path:

**For Realtrack (transactions):**
1. JSON file → `stg_transactions` table (raw JSON stored as-is)
2. JSON parsed → `transactions` table (normalized columns)
3. Address from transactions → `properties` table created/updated

**For Brand Locations:**
1. Scraper → `brand_locations` table directly (already has separate address fields)
2. Address from brand_locations → `properties` table created/updated

**Key Point:** The `properties` table is a DERIVATIVE. It's populated from TWO different raw sources with DIFFERENT address formats.

---

## 1. RAW DATA SOURCES

### Source 1: Transactions Table (Realtrack Scraper)

**Raw Format:**
```json
{
  "Address": "251 - 255 DAVENPORT RD",
  "City": "Toronto",
  "AlternateAddress1": "",
  "AlternateAddress2": "",
  "AlternateAddress3": "",
  "ARN": "",
  "PIN": "126750004"
}
```

**Stored in `transactions` table as:**
- `address_raw`: "251 - 255 DAVENPORT RD" (single string)
- `city_raw`: "Toronto" (single string)
- `alt_address1`, `alt_address2`, `alt_address3`: Alternative addresses
- `arn`: Assessment Roll Number
- `pin`: Property Identification Number
- **NO POSTAL CODE** in raw Realtrack data

**Key Observations:**
- ✅ Has city in raw data
- ❌ NO postal code
- ✅ Has ARN/PIN identifiers
- ✅ Has alternate addresses

### Source 2: Brand Locations Table (Brand Scraper)

**Stored in `brand_locations` table as:**
- `address_line1`: "1650 Victoria Street East" (street address)
- `city`: "Whitby" (city name)
- `province`: "ON" (province code)
- `postal_code`: "L1N 9L4" (POSTAL CODE!)
- `country`: "Canada"

**Key Observations:**
- ✅ Has city in separate field
- ✅ HAS postal code!
- ✅ Has province
- ✅ Has country
- ⚠️ Address may include city prefix (e.g., "St. Catharines 212 Welland Avenue")
- ⚠️ Address may include unit numbers (e.g., "#Unit 1", "#Unit 204")

---

## 2. ADDRESS FORMAT VARIATIONS

### From TRANSACTIONS (Realtrack):

#### Variation 1: Hyphenated Range
```
"251 - 255 DAVENPORT RD", "Toronto"
"745 - 747 ST CLAIR ST", "Chatham-Kent"
"1398 - 1402 HIGHGATE RD", "Ottawa"
```
**Pattern:** `NUMBER - NUMBER STREET`

#### Variation 2: Ampersand Separator
```
"8 & 14 FOREST AVE", "Hamilton"
```
**Pattern:** `NUMBER & NUMBER STREET`

#### Variation 3: Simple Address
```
"11318 GUELPH LINE", "Milton"
"31 BEACH DR", "Wasaga Beach"
"71 DUNDAS ST E", "Paris"
```
**Pattern:** `NUMBER STREET`

#### Variation 4: Multiple Addresses in Alt Fields
```
address_raw: "31 BEACH DR"
alt_address1: "41 - 47 BEACH DR"
alt_address2: "57 - 59 BEACH DR"
alt_address3: "91 - 93 BEACH DR"
```
**Pattern:** Primary + up to 3 alternates

### From BRAND_LOCATIONS:

#### Variation 5: City Prefix
```
"St. Catharines 212 Welland Avenue", "St. Catharines", "ON", "L2R 2P2"
"Sault Ste. Marie 153 Great Northern Road", "Sault Ste. Marie", "ON", "P6A 6N1"
"Niagara Falls 6380 Fallsview Boulevard", "Niagara Falls", "ON", "L2G 7X5"
```
**Pattern:** `CITY NUMBER STREET` (city is duplicated in address_line1 AND city field)

#### Variation 6: Unit Numbers
```
"973 Montréal Road #Unit 1", "Ottawa", "ON", "K1K 0S6"
"Niagara Falls 6380 Fallsview Boulevard #Unit 204", "Niagara Falls", "ON", "L2G 7Y6"
"2014 Ogilvie Road #Unit 1", "Ottawa", "ON", "K1J 7N9"
```
**Pattern:** `NUMBER STREET #Unit X` or `NUMBER STREET #Unit 204`

#### Variation 7: Simple Address (with postal!)
```
"1650 Victoria Street East", "Whitby", "ON", "L1N 9L4"
"1700 Wilson Avenue", "Toronto", "ON", "M3L 1B2"
"1900 Cyrville Road", "Ottawa (Gloucester)", "ON", "K1B 1A5"
```
**Pattern:** `NUMBER STREET` + postal code in separate field

#### Variation 8: City with Parenthetical
```
"4679 Kingston Rd", "Toronto (Scarborough)", "ON", "M1E 2P8"
"1900 Cyrville Road", "Ottawa (Gloucester)", "ON", "K1B 1A5"
```
**Pattern:** City field contains `CITY (SUBURB)` format

---

## 3. HOW DATA FLOWS TO PROPERTIES TABLE

### Step 1: Realtrack Ingest (transactions → properties)

**Script:** `scripts/scraper/realtrack_ingest.py`

**What happens:**
1. JSON file loaded
2. For each transaction:
   - `address_raw` = rec.get("Address") → becomes `address_line1`
   - `city_raw` = rec.get("City") → becomes `city`
   - NO postal code (not in Realtrack data)
   - `alt_address1/2/3` stored
   - Creates/updates property via `find_or_create_property()`

**Code:**
```python
# Line 91-92 in realtrack_ingest.py
prop_id = find_or_create_property(
    cur,
    addr_hash_raw,
    address=addr,  # Goes to address_line1
    city=city,     # Goes to city
    arn=(rec.get("ARN") or None),
    pin=(rec.get("PIN") or None),
    alt1=(rec.get("AlternateAddress1") or None),
    alt2=(rec.get("AlternateAddress2") or None),
    alt3=(rec.get("AlternateAddress3") or None),
)
```

**Properties table gets:**
- `address_line1`: From address_raw
- `city`: From city_raw
- `postal_code`: NULL (Realtrack doesn't have it!)
- `alt_address1/2/3`: From Realtrack alternate addresses
- `arn`, `pin`: From Realtrack

### Step 2: Brand Locations (brand_locations → properties)

**Properties table gets:**
- `address_line1`: From brand_locations.address_line1
- `city`: From brand_locations.city
- `postal_code`: From brand_locations.postal_code ✅
- `province`: From brand_locations.province

---

## 4. THE PROBLEM WITH CURRENT NORMALIZATION

### Issue 1: Realtrack Data Has NO Postal Codes
- 60 properties with postal codes failed NAR validation
- But Realtrack raw data NEVER had postal codes!
- **Where did those postal codes come from?** → They must be from:
  1. Geocoding backfill (geocodio API added them)
  2. OR from brand_locations if property linked to both sources

### Issue 2: Different Address Formats Not Parsed Consistently
- Hyphenated ranges: "251 - 255" stored as-is, not parsed
- City prefixes: "St. Catharines 212 Welland Avenue" not cleaned
- Unit numbers: "#Unit 1" stored in address_line1

### Issue 3: City Normalization Happened AFTER Import
- Raw data goes to `city` field
- Then `normalize_city()` was called somewhere
- Original city backed up to `city_backup`
- But normalization logic was inconsistent

---

## 5. CURRENT STATE OF PROPERTIES TABLE

### Fields Populated at Import Time:
- `address_line1`: From raw scraper (varies by source)
- `city`: From raw scraper (varies by source)
- `city_backup`: Original city before normalization
- `postal_code`: Only from brand_locations OR geocoding
- `alt_address1/2/3`: Only from Realtrack
- `arn`, `pin`: Only from Realtrack

### Fields Populated by Standardization Script:
**Script:** `scripts/db/standardize_properties.py`

- `address_canonical`: Computed from address_line1 + city + province
- `address_hash`: SHA256 of canonical address
- `latitude`, `longitude`: From Geocodio API
- `geocode_source`: "geocodio"
- `geocode_accuracy`: From Geocodio
- `geom`: PostGIS geography point

**Code:**
```python
# Lines 22-23 in standardize_properties.py
canonical = canonicalize_address(address_line1, city, province, country)
address_hash = hash_canonical_address(address_line1, city, province, country)
```

### Fields Populated by NAR Validation:
- `city`: MAY be updated if confidence ≥90
- `postal_code`: MAY be added if found in NAR
- `latitude`, `longitude`: MAY be updated if found in NAR
- `geocode_source`: Changed to "nar_query"

---

## 6. ROOT CAUSE ANALYSIS

### Why Normalization Failed:

1. **Two Different Raw Formats**
   - Realtrack: Single string address + city (no postal)
   - Brand Locations: Structured fields (has postal)

2. **No Unified Parsing Step**
   - Address_line1 stored "as-is" from scrapers
   - No preprocessing to extract:
     - Street number
     - Street name
     - Unit number
     - City prefix

3. **Normalization Logic Applied Too Late**
   - City normalization happened AFTER import
   - But no address parsing happened at all

4. **NAR Validation Assumed Clean Data**
   - Expected: "123 Main St"
   - Got: "St. Catharines 212 Welland Avenue"
   - Result: Failed to parse street number

---

## 7. SUMMARY

### RAW DATA SOURCES:
1. **transactions**: Realtrack scraper (NO postal codes)
2. **brand_locations**: Brand scraper (HAS postal codes)

### RAW DATA GETS STORED IN:
- **properties** table (derivative of both sources)

### ADDRESS FORMATS FOUND:
1. Hyphenated ranges: "251 - 255 DAVENPORT RD"
2. Ampersand separator: "8 & 14 FOREST AVE"
3. City prefix: "St. Catharines 212 Welland Avenue"
4. Unit numbers: "973 Montréal Road #Unit 1"
5. Simple: "11318 GUELPH LINE"
6. City with suburb: "Toronto (Scarborough)"

### CURRENT PIPELINE:
```
Raw Scraper Data
    ↓
transactions / brand_locations (raw tables)
    ↓
properties table (derivative - NO PARSING!)
    ↓
standardize_properties.py (canonicalize + geocode)
    ↓
NAR validation (tries to validate messy data)
```

### THE MISSING STEP:
**Address parsing/preprocessing BEFORE normalization**
- Extract street number (handle ranges, prefixes)
- Extract street name
- Strip unit numbers
- Remove city prefixes
- Store cleaned components in separate fields
