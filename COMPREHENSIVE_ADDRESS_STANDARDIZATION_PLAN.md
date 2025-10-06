# Comprehensive Address Standardization Plan

**Date:** 2025-10-03
**Status:** PROPOSAL - Awaiting User Approval

---

## OVERVIEW

This plan establishes a systematic, multi-stage pipeline for address standardization:
1. **Raw Ingestion** - Get minimum viable address data from scrapers
2. **Parsing** - Use libpostal to parse into standard components
3. **Standardization** - Verify and clean addresses through multi-step validation

---

# STAGE 1: RAW DATA INGESTION

## Goal
Ensure scrapers capture minimum required address data

## Minimum Requirements Per Source

### Realtrack Scraper
**Current State:**
- ✅ Has: address_raw, city_raw, ARN, PIN
- ❌ Missing: postal_code

**Action Required:**
- Check if Realtrack provides postal codes (likely not)
- If not, document that postal codes will come from NAR/geocoding only

### Brand Locations Scraper
**Current State:**
- ✅ Has: address_line1, city, province, postal_code
- ✅ Complete

### Future Scrapers
**Required Fields:**
- `address_raw` (full address string) OR
- `street_number` + `street_name` (components)
- `city` OR `postal_code` (at least one)
- `province` (preferred)

---

# STAGE 2: ADDRESS PARSING (NEW!)

## 2.1: What is libpostal?

**libpostal** is an open-source library for parsing addresses into components using machine learning.

**Features:**
- Trained on global address data (including Canada)
- Handles messy, unstructured addresses
- Parses into components: house_number, road, city, postcode, etc.
- Supports 60+ countries

**Example:**
```python
from postal.parser import parse_address

address = "St. Catharines 212 Welland Avenue #Unit 5, ON L2R 2P2"

parsed = parse_address(address)
# Returns:
# [
#   ('st. catharines', 'city'),
#   ('212', 'house_number'),
#   ('welland avenue', 'road'),
#   ('unit 5', 'unit'),
#   ('on', 'state'),
#   ('l2r 2p2', 'postcode')
# ]
```

## 2.2: Installation

```bash
# Install libpostal C library (one-time setup)
# macOS:
brew install libpostal

# Python wrapper
pip install postal
```

## 2.3: New Table: `parsed_addresses`

**Schema:**
```sql
CREATE TABLE parsed_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source reference
    source_table VARCHAR NOT NULL,  -- 'transactions' or 'brand_locations'
    source_id UUID NOT NULL,        -- ID from source table

    -- Raw input
    address_raw TEXT NOT NULL,
    city_raw VARCHAR,
    postal_code_raw VARCHAR,
    province_raw VARCHAR,

    -- Parsed components (from libpostal)
    house_number VARCHAR,
    road VARCHAR,
    unit VARCHAR,
    city_parsed VARCHAR,
    suburb VARCHAR,
    postcode_parsed VARCHAR,
    province_parsed VARCHAR,
    country_parsed VARCHAR,

    -- Metadata
    parser_version VARCHAR,        -- 'libpostal-1.1'
    parsed_at TIMESTAMP DEFAULT NOW(),
    parse_confidence JSONB,        -- Store libpostal confidence scores

    -- Indexes
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_parsed_addresses_source ON parsed_addresses(source_table, source_id);
CREATE INDEX idx_parsed_addresses_postcode ON parsed_addresses(postcode_parsed);
CREATE INDEX idx_parsed_addresses_city ON parsed_addresses(city_parsed);
```

## 2.4: Parsing Script

**Script:** `scripts/parsing/parse_addresses.py`

```python
#!/usr/bin/env python3
"""
Parse addresses from raw tables into parsed_addresses table.
"""
from postal.parser import parse_address
from common.db import connect_with_retries

def parse_transaction_address(record):
    """Parse address from transactions table."""
    # Build full address string
    parts = []
    if record['address_raw']:
        parts.append(record['address_raw'])
    if record['city_raw']:
        parts.append(record['city_raw'])

    address_full = ', '.join(parts)

    # Parse with libpostal
    components = parse_address(address_full)

    # Convert to dict
    parsed = {}
    for value, label in components:
        if label == 'house_number':
            parsed['house_number'] = value
        elif label == 'road':
            parsed['road'] = value
        elif label == 'unit':
            parsed['unit'] = value
        elif label == 'city':
            parsed['city_parsed'] = value
        elif label == 'suburb':
            parsed['suburb'] = value
        elif label == 'postcode':
            parsed['postcode_parsed'] = value
        elif label == 'state':
            parsed['province_parsed'] = value
        elif label == 'country':
            parsed['country_parsed'] = value

    return {
        'source_table': 'transactions',
        'source_id': record['id'],
        'address_raw': record['address_raw'],
        'city_raw': record['city_raw'],
        'postal_code_raw': None,  # Realtrack doesn't have postal
        'province_raw': None,
        **parsed,
        'parser_version': 'libpostal-1.1'
    }

def parse_brand_location_address(record):
    """Parse address from brand_locations table."""
    # Build full address string
    parts = []
    if record['address_line1']:
        parts.append(record['address_line1'])
    if record['city']:
        parts.append(record['city'])
    if record['province']:
        parts.append(record['province'])
    if record['postal_code']:
        parts.append(record['postal_code'])

    address_full = ', '.join(parts)

    # Parse with libpostal
    components = parse_address(address_full)

    # Convert to dict (same as above)
    parsed = {}
    for value, label in components:
        if label == 'house_number':
            parsed['house_number'] = value
        elif label == 'road':
            parsed['road'] = value
        # ... (same logic as above)

    return {
        'source_table': 'brand_locations',
        'source_id': record['id'],
        'address_raw': record['address_line1'],
        'city_raw': record['city'],
        'postal_code_raw': record['postal_code'],
        'province_raw': record['province'],
        **parsed,
        'parser_version': 'libpostal-1.1'
    }
```

---

# STAGE 3: STANDARDIZATION & VALIDATION

## 3.1: Hyphenated Address Strategy

**Problem:**
- "251 - 255 DAVENPORT RD" could be any of: 251, 252, 253, 254, 255

**Question for User:**
Which strategy do you prefer?

### Option A: Try All Numbers (Exhaustive)
**Approach:** Generate all possible addresses in range, try each against NAR

```python
def expand_address_range(house_number: str, road: str, city: str):
    """
    Expand hyphenated range into list of addresses to try.

    Example: "251-255" → ["251", "252", "253", "254", "255"]
    """
    if '-' not in house_number:
        return [house_number]

    # Parse range
    parts = house_number.split('-')
    if len(parts) != 2:
        return [house_number]

    try:
        start = int(parts[0].strip())
        end = int(parts[1].strip())

        # Generate all numbers in range
        return [str(n) for n in range(start, end + 1)]
    except ValueError:
        return [house_number]

# Usage:
candidates = expand_address_range("251-255", "DAVENPORT RD", "Toronto")
# Try each: ["251 DAVENPORT RD", "252 DAVENPORT RD", ...]

for number in candidates:
    result = query_nar(number, "DAVENPORT RD", "Toronto")
    if result:
        return result  # Found a match!
```

**Pros:**
- Most thorough
- Will find the address if ANY number in range exists in NAR

**Cons:**
- Could query NAR 5+ times per address
- Slower

### Option B: Try First and Last Only
**Approach:** Only try the endpoints of the range

```python
candidates = ["251", "255"]  # Just first and last
```

**Pros:**
- Faster (only 2 queries)

**Cons:**
- Might miss the correct address

### Option C: Use First Number Only
**Approach:** Always use the first number in the range

```python
candidates = ["251"]  # Just the first
```

**Pros:**
- Fastest (1 query)
- Consistent

**Cons:**
- Might not match NAR if NAR has different number

**Recommendation:** Start with **Option A** (exhaustive). If performance becomes an issue, optimize to Option B.

## 3.2: City Verification Strategy

**Goal:** Verify city with 100% confidence before validating address

### Step 1: Postal Code → City Lookup (95% confidence)

```python
def verify_city_by_postal(postal_code: str) -> Optional[str]:
    """
    Query NAR by postal code to get city.

    Returns: City name if found, None otherwise
    """
    if not postal_code:
        return None

    query = """
        SELECT city, COUNT(*) as count
        FROM read_parquet('data/nar/addresses.geo.parquet')
        WHERE country = 'CA'
          AND state = 'ON'
          AND REPLACE(UPPER(zipcode), ' ', '') = ?
        GROUP BY city
        ORDER BY count DESC
        LIMIT 1
    """

    result = duckdb.execute(query, [postal_code.replace(' ', '').upper()]).fetchone()

    if result:
        return result[0]  # Return city

    return None
```

**If postal code found:**
- City = NAR result
- Confidence = 95%
- **Proceed to address validation**

### Step 2: Check if City Exists in NAR (if no postal code)

```python
def verify_city_in_nar(city: str) -> bool:
    """
    Check if city exists in NAR database.

    Returns: True if city found, False otherwise
    """
    query = """
        SELECT COUNT(*) as count
        FROM read_parquet('data/nar/addresses.geo.parquet')
        WHERE country = 'CA'
          AND state = 'ON'
          AND UPPER(city) = ?
        LIMIT 1
    """

    result = duckdb.execute(query, [city.upper()]).fetchone()

    return result[0] > 0 if result else False
```

**If exact city match found:**
- City = raw city value
- Confidence = 90%
- **Proceed to address validation**

### Step 3: Check for City Amalgamations/Alternate Names

**Ontario City Amalgamations:**
```python
CITY_AMALGAMATIONS = {
    # Amalgamated city → List of former municipalities
    'TORONTO': [
        'ETOBICOKE', 'NORTH YORK', 'SCARBOROUGH',
        'YORK', 'EAST YORK'
    ],
    'OTTAWA': [
        'NEPEAN', 'GLOUCESTER', 'KANATA', 'ORLEANS',
        'VANIER', 'CUMBERLAND', 'OSGOODE', 'RIDEAU',
        'WEST CARLETON', 'GOULBOURN', 'ROCKCLIFFE PARK'
    ],
    'HAMILTON': [
        'DUNDAS', 'FLAMBOROUGH', 'GLANBROOK', 'STONEY CREEK', 'ANCASTER'
    ],
    'GREATER SUDBURY': [
        'SUDBURY', 'VALLEY EAST', 'RAYSIDE-BALFOUR', 'ONAPING FALLS',
        'WALDEN', 'NICKEL CENTRE', 'CAPREOL'
    ],
    'CHATHAM-KENT': [
        'CHATHAM', 'WALLACEBURG', 'TILBURY', 'BLENHEIM', 'DRESDEN'
    ],
    # ... more
}

# Reverse lookup
AMALGAMATION_REVERSE = {}
for amalgamated, former_list in CITY_AMALGAMATIONS.items():
    for former in former_list:
        AMALGAMATION_REVERSE[former] = amalgamated
```

```python
def check_city_amalgamation(city: str) -> Optional[str]:
    """
    Check if city is a former municipality now amalgamated.

    Returns: Amalgamated city name if found, None otherwise
    """
    city_upper = city.upper().strip()

    # Check if this is a former municipality
    if city_upper in AMALGAMATION_REVERSE:
        amalgamated_city = AMALGAMATION_REVERSE[city_upper]

        # Verify amalgamated city exists in NAR
        if verify_city_in_nar(amalgamated_city):
            return amalgamated_city

    return None
```

**If amalgamation found:**
- City = amalgamated city
- Confidence = 85%
- **Proceed to address validation**

### Step 4: Fuzzy Match City

```python
from rapidfuzz import process, fuzz

def fuzzy_match_city(city: str, nar_cities: list[str]) -> Optional[tuple[str, int]]:
    """
    Fuzzy match city against NAR cities.

    Returns: (best_match, score) or None
    """
    if not city:
        return None

    # Use rapidfuzz to find best match
    result = process.extractOne(
        city.upper(),
        nar_cities,
        scorer=fuzz.ratio,
        score_cutoff=85  # Require 85% match
    )

    if result:
        match, score, _ = result
        return (match, score)

    return None
```

**Get NAR cities once:**
```python
def get_nar_cities() -> list[str]:
    """Get list of all cities in NAR."""
    query = """
        SELECT DISTINCT city
        FROM read_parquet('data/nar/addresses.geo.parquet')
        WHERE country = 'CA' AND state = 'ON'
        ORDER BY city
    """

    result = duckdb.execute(query).fetchall()
    return [row[0] for row in result]
```

**If fuzzy match found (score ≥85):**
- City = fuzzy matched city
- Confidence = score
- **Proceed to address validation if score ≥85**

### Step 5: Google Geocoding API (Last Resort)

```python
def verify_city_via_google(address: str, city: str) -> Optional[str]:
    """
    Use Google Geocoding API to verify city.

    Returns: City from Google or None
    """
    from googlemaps import Client

    gmaps = Client(key=os.getenv('GOOGLE_API_KEY'))

    # Geocode full address
    full_address = f"{address}, {city}, ON, Canada"

    result = gmaps.geocode(full_address)

    if result:
        # Extract city from address components
        for component in result[0]['address_components']:
            if 'locality' in component['types']:
                return component['long_name']

    return None
```

**If Google returns city:**
- City = Google result
- Confidence = 75%
- **Proceed to address validation**

**If no city verification succeeds:**
- Mark as "city_unverified"
- Confidence = 0%
- **Skip address validation, keep original city**

## 3.3: Complete Standardization Workflow

```
┌─────────────────────────────────┐
│  PARSED ADDRESS (libpostal)     │
│  - house_number: "251-255"      │
│  - road: "DAVENPORT RD"         │
│  - city_parsed: "Toronto"       │
│  - postcode_parsed: "M5R 1J9"   │
└─────────────────────────────────┘
              ↓
┌─────────────────────────────────┐
│  STEP 1: Verify City            │
└─────────────────────────────────┘
              ↓
    ┌─────────────────┐
    │ Has postal code?│
    └─────────────────┘
         ↓ YES         ↓ NO
         ↓             ↓
    Query NAR by    Check exact
    postal code     city in NAR
         ↓             ↓
    City found?    City found?
         ↓ YES         ↓ NO
         ↓             ↓
    Use NAR city   Check amalgamation
         ↓             ↓
    Confidence=95  Amalgamated?
         ↓             ↓ YES
         ↓        Use amalgamated
         ↓             ↓
         ↓        Confidence=85
         ↓             ↓ NO
         ↓             ↓
         ↓        Fuzzy match
         ↓             ↓
         ↓        Match ≥85?
         ↓             ↓ YES
         ↓        Use fuzzy match
         ↓             ↓
         ↓        Confidence=score
         ↓             ↓ NO
         ↓             ↓
         ↓        Google API?
         ↓             ↓
         ↓        City found?
         ↓             ↓ YES
         ↓        Use Google
         ↓             ↓
         ↓        Confidence=75
         ↓             ↓ NO
         ↓             ↓
         ↓        FAILED
         ↓             ↓
         └─────────────┘
              ↓
┌─────────────────────────────────┐
│  CITY VERIFIED                  │
│  city_verified = "TORONTO"      │
│  city_confidence = 95           │
└─────────────────────────────────┘
              ↓
┌─────────────────────────────────┐
│  STEP 2: Expand Hyphenated      │
│         Addresses               │
└─────────────────────────────────┘
              ↓
    "251-255" → ["251", "252", "253", "254", "255"]
              ↓
┌─────────────────────────────────┐
│  STEP 3: Validate Each Address  │
│         Against NAR             │
└─────────────────────────────────┘
              ↓
    FOR EACH number in candidates:
        Query NAR:
          WHERE number = ?
            AND street LIKE ?
            AND city = city_verified

        IF found:
            RETURN result
            confidence = 100

    IF none found:
        confidence = city_confidence
        (trust city, but address not in NAR)
              ↓
┌─────────────────────────────────┐
│  RESULT                         │
│  city: "TORONTO"                │
│  postal_code: "M5R 1J9"         │
│  address: "251 DAVENPORT RD"    │
│  lat/lon: from NAR or geocode   │
│  confidence: 95-100             │
└─────────────────────────────────┘
```

---

# IMPLEMENTATION PLAN

## Phase 1: Setup & Parsing

1. **Install libpostal**
   - Install C library
   - Install Python wrapper
   - Test on sample addresses

2. **Create `parsed_addresses` table**
   - Run migration to create table
   - Add indexes

3. **Build parsing script**
   - `scripts/parsing/parse_addresses.py`
   - Parse transactions table
   - Parse brand_locations table
   - Store in parsed_addresses

4. **Test parsing**
   - Run on 100 sample addresses
   - Review parsed output
   - Adjust if needed

## Phase 2: City Verification

1. **Extract all NAR cities**
   - Query NAR for distinct cities
   - Store in cache file

2. **Build city amalgamation map**
   - Research Ontario amalgamations
   - Create complete mapping

3. **Implement verification functions**
   - Postal → city
   - Exact city match
   - Amalgamation check
   - Fuzzy match
   - Google API (optional)

4. **Test city verification**
   - Run on 100 samples
   - Check success rate
   - Review failures

## Phase 3: Address Validation

1. **Implement hyphenated address expansion**
   - Build range parser
   - Test on samples

2. **Build NAR validation function**
   - Query NAR with verified city
   - Try all candidate numbers
   - Return best match

3. **Test complete workflow**
   - Run on 500 samples
   - Measure success rate
   - Review failures

## Phase 4: Full Migration

1. **Parse all addresses**
   - Run parsing script on all data
   - Monitor progress

2. **Standardize all addresses**
   - Run standardization script
   - Generate report

3. **Update properties table**
   - Populate with standardized data
   - Preserve originals

4. **Validation**
   - Compare before/after
   - Verify no data loss
   - Check success rates

---

# QUESTIONS FOR USER

1. **Hyphenated Addresses:**
   - Option A (try all numbers), B (endpoints), or C (first only)?
   - My recommendation: A

2. **City Verification:**
   - Should we use Google API as fallback? (costs money)
   - Or stop at fuzzy matching?

3. **Confidence Thresholds:**
   - What minimum confidence to update city? (I suggest ≥85)
   - What minimum to update address? (I suggest ≥90)

4. **Schema:**
   - Should we add `street_number`, `street_name`, etc. to `properties` table?
   - Or keep parsed data in separate `parsed_addresses` table?

5. **Testing:**
   - Run full parse on all 16k properties first (read-only)?
   - Or start with 1000 sample for testing?

---

# SUCCESS METRICS

After implementation, we should see:

| Metric | Current | Target |
|--------|---------|--------|
| Addresses parsed | 0% | 100% |
| Cities verified | ~60% | 95%+ |
| Postal codes filled | ~30% | 70%+ |
| NAR matches | 46% | 80%+ |
| High confidence (≥90) | 32% | 75%+ |

Ready for your feedback and direction!
