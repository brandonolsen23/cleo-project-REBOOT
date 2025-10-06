# Address Standardization - Implementation Phases

**Date:** 2025-10-03
**Approach:** Build one piece at a time, verify, then proceed

---

## PHASE 1: Install & Test libpostal

### Goal
Get libpostal working and test basic parsing capability

### Tasks
1. Install libpostal C library
2. Install Python wrapper
3. Test on 10 sample addresses from our data
4. Verify parsing quality

### Deliverable
Python script that can parse addresses and show results

### Success Criteria
- libpostal installed successfully
- Can parse Canadian addresses
- Extracts: house_number, road, city, postcode

### Checkpoint
**STOP** - Review parsed output with user before proceeding

---

## PHASE 2: Parse Transactions Table (Realtrack)

### Goal
Create `transactions_parsed` table and parse all Realtrack addresses

### Tasks
1. Create `transactions_parsed` table schema
2. Write parsing script for transactions
3. Parse 100 sample transactions
4. Review parsing quality
5. Parse remaining transactions (if quality good)

### Schema
```sql
CREATE TABLE transactions_parsed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to source
    transaction_id UUID NOT NULL REFERENCES transactions(id),

    -- Raw input
    address_raw TEXT,
    city_raw VARCHAR,

    -- Parsed components (from libpostal)
    house_number VARCHAR,
    road VARCHAR,
    unit VARCHAR,
    city_parsed VARCHAR,
    suburb VARCHAR,
    postcode_parsed VARCHAR,
    province_parsed VARCHAR,

    -- Metadata
    parser_version VARCHAR DEFAULT 'libpostal-1.1',
    parsed_at TIMESTAMP DEFAULT NOW(),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(transaction_id)
);

CREATE INDEX idx_transactions_parsed_transaction ON transactions_parsed(transaction_id);
CREATE INDEX idx_transactions_parsed_city ON transactions_parsed(city_parsed);
```

### Deliverable
- `transactions_parsed` table populated
- Report showing parse success rate

### Success Criteria
- 95%+ addresses have house_number extracted
- 95%+ addresses have road extracted
- 90%+ addresses have city_parsed extracted

### Checkpoint
**STOP** - Review sample of 50 parsed addresses with user

---

## PHASE 3: Parse Brand Locations Table

### Goal
Create `brand_locations_parsed` table and parse all brand location addresses

### Tasks
1. Create `brand_locations_parsed` table schema
2. Write parsing script for brand_locations
3. Parse 100 sample brand locations
4. Review parsing quality
5. Parse remaining brand locations (if quality good)

### Schema
```sql
CREATE TABLE brand_locations_parsed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to source
    brand_location_id UUID NOT NULL REFERENCES brand_locations(id),

    -- Raw input
    address_raw TEXT,
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

    -- Metadata
    parser_version VARCHAR DEFAULT 'libpostal-1.1',
    parsed_at TIMESTAMP DEFAULT NOW(),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(brand_location_id)
);

CREATE INDEX idx_brand_locations_parsed_location ON brand_locations_parsed(brand_location_id);
CREATE INDEX idx_brand_locations_parsed_city ON brand_locations_parsed(city_parsed);
```

### Deliverable
- `brand_locations_parsed` table populated
- Report showing parse success rate

### Success Criteria
- 95%+ addresses have house_number extracted
- 95%+ addresses have road extracted
- 90%+ addresses have city_parsed extracted
- 80%+ addresses have postcode_parsed extracted

### Checkpoint
**STOP** - Review sample of 50 parsed addresses with user

---

## PHASE 4: City Verification - Postal Code Lookup

### Goal
Verify cities using postal code → NAR lookup

### Tasks
1. Create `address_standardization` table to track verification steps
2. Write postal code → city lookup function
3. Test on 100 addresses WITH postal codes
4. Review accuracy

### Schema
```sql
CREATE TABLE address_standardization (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to parsed address
    source_table VARCHAR NOT NULL,  -- 'transactions_parsed' or 'brand_locations_parsed'
    source_id UUID NOT NULL,

    -- Verification steps (track the waterfall)
    city_verification_method VARCHAR,  -- 'postal_code', 'exact_match', 'amalgamation', 'fuzzy', 'google'
    city_verified VARCHAR,
    city_confidence INT,

    -- Address verification
    address_verified VARCHAR,
    address_confidence INT,

    -- NAR results (if found)
    nar_found BOOLEAN DEFAULT FALSE,
    nar_city VARCHAR,
    nar_postal_code VARCHAR,
    nar_latitude FLOAT,
    nar_longitude FLOAT,

    -- Final standardized address
    final_house_number VARCHAR,
    final_road VARCHAR,
    final_unit VARCHAR,
    final_city VARCHAR,
    final_postal_code VARCHAR,
    final_latitude FLOAT,
    final_longitude FLOAT,
    final_confidence INT,

    -- Metadata
    standardized_at TIMESTAMP DEFAULT NOW(),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_standardization_source ON address_standardization(source_table, source_id);
CREATE INDEX idx_standardization_city ON address_standardization(city_verified);
```

### Function
```python
def verify_city_by_postal(postal_code: str) -> Optional[tuple[str, int]]:
    """
    Query NAR by postal code to get city.

    Returns: (city, confidence) or None
    """
    if not postal_code:
        return None

    # Clean postal code
    postal_clean = postal_code.strip().upper().replace(' ', '')
    if len(postal_clean) != 6:
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

    result = duckdb.execute(query, [postal_clean]).fetchone()

    if result:
        return (result[0], 95)  # 95% confidence

    return None
```

### Test Script
```python
# Test on 100 addresses with postal codes
# Show:
# - How many postal codes valid (6 chars)
# - How many found in NAR
# - City matches between parsed and NAR
```

### Deliverable
- Function that verifies city by postal code
- Test report on 100 samples

### Success Criteria
- 90%+ valid postal codes found in NAR
- Cities returned make sense

### Checkpoint
**STOP** - Review postal code verification results with user

---

## PHASE 5: City Verification - Exact Match

### Goal
For addresses WITHOUT postal codes, check if city exists in NAR

### Tasks
1. Extract all distinct cities from NAR (one-time)
2. Write exact city match function
3. Test on 100 addresses WITHOUT postal codes
4. Review accuracy

### Function
```python
# Load NAR cities once (cache in file)
def load_nar_cities() -> set[str]:
    """Load all cities from NAR into memory."""
    query = """
        SELECT DISTINCT UPPER(city) as city
        FROM read_parquet('data/nar/addresses.geo.parquet')
        WHERE country = 'CA' AND state = 'ON'
    """

    result = duckdb.execute(query).fetchall()
    return {row[0] for row in result}

# Check if city exists
def verify_city_exact(city: str, nar_cities: set[str]) -> Optional[tuple[str, int]]:
    """
    Check if city exists exactly in NAR.

    Returns: (city, confidence) or None
    """
    if not city:
        return None

    city_upper = city.strip().upper()

    if city_upper in nar_cities:
        return (city_upper, 90)  # 90% confidence

    return None
```

### Deliverable
- Function that checks exact city match
- Test report on 100 samples

### Success Criteria
- Can identify when city is valid
- Can identify when city is NOT in NAR

### Checkpoint
**STOP** - Review exact match results with user

---

## PHASE 6: City Verification - Amalgamation Check

### Goal
Map old municipality names to current amalgamated cities

### Tasks
1. Research and create complete Ontario amalgamation map
2. Write amalgamation check function
3. Test on addresses with old city names
4. Review accuracy

### Data
```python
CITY_AMALGAMATIONS = {
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
        'DUNDAS', 'FLAMBOROUGH', 'GLANBROOK',
        'STONEY CREEK', 'ANCASTER'
    ],
    'GREATER SUDBURY': [
        'SUDBURY', 'VALLEY EAST', 'RAYSIDE-BALFOUR',
        'ONAPING FALLS', 'WALDEN', 'NICKEL CENTRE', 'CAPREOL'
    ],
    'CHATHAM-KENT': [
        'CHATHAM', 'WALLACEBURG', 'TILBURY', 'BLENHEIM',
        'DRESDEN', 'RIDGETOWN'
    ],
    # TODO: Research and add more
}

# Build reverse lookup
AMALGAMATION_REVERSE = {}
for amalgamated, former_list in CITY_AMALGAMATIONS.items():
    for former in former_list:
        AMALGAMATION_REVERSE[former] = amalgamated
```

### Function
```python
def verify_city_amalgamation(city: str, nar_cities: set[str]) -> Optional[tuple[str, int]]:
    """
    Check if city is a former municipality.

    Returns: (amalgamated_city, confidence) or None
    """
    if not city:
        return None

    city_upper = city.strip().upper()

    # Check if this is a former municipality
    if city_upper in AMALGAMATION_REVERSE:
        amalgamated = AMALGAMATION_REVERSE[city_upper]

        # Verify amalgamated city exists in NAR
        if amalgamated in nar_cities:
            return (amalgamated, 85)  # 85% confidence

    return None
```

### Deliverable
- Complete amalgamation mapping
- Function that checks amalgamations
- Test report

### Success Criteria
- Correctly maps former municipalities
- Returns current city names

### Checkpoint
**STOP** - Review amalgamation mapping with user

---

## PHASE 7: City Verification - Fuzzy Match

### Goal
Handle typos and minor variations in city names

### Tasks
1. Install rapidfuzz library
2. Write fuzzy match function
3. Test on addresses with misspelled cities
4. Review accuracy (ensure no false positives)

### Function
```python
from rapidfuzz import process, fuzz

def verify_city_fuzzy(city: str, nar_cities: list[str]) -> Optional[tuple[str, int]]:
    """
    Fuzzy match city against NAR cities.

    Returns: (matched_city, confidence_score) or None
    """
    if not city:
        return None

    city_upper = city.strip().upper()

    # Use rapidfuzz to find best match
    result = process.extractOne(
        city_upper,
        nar_cities,
        scorer=fuzz.ratio,
        score_cutoff=85  # Require 85% similarity
    )

    if result:
        match, score, _ = result
        return (match, score)  # score = confidence

    return None
```

### Deliverable
- Function that fuzzy matches cities
- Test report showing matches and scores

### Success Criteria
- Correctly matches typos (e.g., "Tornto" → "TORONTO")
- Does NOT create false matches
- Score threshold (85) is appropriate

### Checkpoint
**STOP** - Review fuzzy match results with user (IMPORTANT: check for false positives!)

---

## PHASE 8: Hyphenated Address Expansion

### Goal
Expand address ranges into individual candidate addresses

### Tasks
1. Write function to detect hyphenated ranges
2. Write function to expand range into list
3. Test on sample hyphenated addresses
4. Review expansion logic

### Function
```python
def expand_address_range(house_number: str) -> list[str]:
    """
    Expand hyphenated range into list of candidate numbers.

    Examples:
        "251-255" → ["251", "252", "253", "254", "255"]
        "8 - 14" → ["8", "9", "10", "11", "12", "13", "14"]
        "123" → ["123"]

    Returns: List of candidate house numbers to try
    """
    if not house_number:
        return []

    # Remove spaces around hyphen
    normalized = house_number.strip().replace(' - ', '-')

    # Check if contains hyphen
    if '-' not in normalized:
        return [house_number]

    # Split on hyphen
    parts = normalized.split('-')
    if len(parts) != 2:
        return [house_number]  # Invalid format, return as-is

    try:
        # Parse start and end
        start = int(parts[0].strip())
        end = int(parts[1].strip())

        # Generate all numbers in range (inclusive)
        candidates = [str(n) for n in range(start, end + 1)]

        return candidates
    except ValueError:
        # Not valid integers, return original
        return [house_number]
```

### Deliverable
- Function that expands hyphenated ranges
- Test showing expansions for various formats

### Success Criteria
- Correctly expands "251-255" → ["251", "252", "253", "254", "255"]
- Handles spaces: "8 - 14" → ["8", "9", "10", "11", "12", "13", "14"]
- Returns original if not a range: "123" → ["123"]

### Checkpoint
**STOP** - Review expansion logic with user

---

## PHASE 9: NAR Address Validation

### Goal
Validate full address against NAR using verified city

### Tasks
1. Write NAR query function
2. Test on 100 addresses with verified cities
3. Handle hyphenated addresses (try all candidates)
4. Review match rate

### Function
```python
def validate_address_in_nar(
    house_number: str,
    road: str,
    city_verified: str
) -> Optional[dict]:
    """
    Query NAR to validate address.

    Returns: NAR record if found, None otherwise
    """
    if not house_number or not road or not city_verified:
        return None

    # Expand hyphenated range
    candidates = expand_address_range(house_number)

    # Try each candidate
    for number in candidates:
        query = """
            SELECT city, zipcode, latitude, longitude
            FROM read_parquet('data/nar/addresses.geo.parquet')
            WHERE country = 'CA'
              AND state = 'ON'
              AND CAST(number AS VARCHAR) = ?
              AND UPPER(street) LIKE ?
              AND UPPER(city) = ?
            LIMIT 1
        """

        # Normalize road for query
        road_normalized = road.upper().strip()

        result = duckdb.execute(
            query,
            [number, f"%{road_normalized}%", city_verified]
        ).fetchone()

        if result:
            return {
                'house_number': number,  # The matched number
                'city': result[0],
                'postal_code': result[1],
                'latitude': result[2],
                'longitude': result[3],
                'confidence': 100  # Perfect match
            }

    # No match found
    return None
```

### Deliverable
- Function that validates addresses in NAR
- Test report showing match rate

### Success Criteria
- Successfully queries NAR
- Tries all candidates for hyphenated addresses
- Returns match with coordinates

### Checkpoint
**STOP** - Review NAR validation results with user

---

## PHASE 10: Full Integration & Testing

### Goal
Run complete standardization pipeline on 1000 sample addresses

### Tasks
1. Combine all verification steps into single workflow
2. Run on 1000 addresses (500 from transactions, 500 from brand_locations)
3. Generate comprehensive report
4. Review results with user

### Workflow
```python
def standardize_address(parsed_address: dict) -> dict:
    """
    Complete standardization workflow.

    Input: Parsed address from libpostal
    Output: Standardized address with confidence scores
    """
    result = {
        'city_verification_method': None,
        'city_verified': None,
        'city_confidence': 0,
        'address_verified': None,
        'address_confidence': 0,
        'nar_found': False,
    }

    # STEP 1: Verify City (waterfall)

    # 1a. Try postal code
    if parsed_address.get('postcode_parsed'):
        city_result = verify_city_by_postal(parsed_address['postcode_parsed'])
        if city_result:
            result['city_verified'], result['city_confidence'] = city_result
            result['city_verification_method'] = 'postal_code'

    # 1b. Try exact match
    if not result['city_verified'] and parsed_address.get('city_parsed'):
        city_result = verify_city_exact(parsed_address['city_parsed'], nar_cities)
        if city_result:
            result['city_verified'], result['city_confidence'] = city_result
            result['city_verification_method'] = 'exact_match'

    # 1c. Try amalgamation
    if not result['city_verified'] and parsed_address.get('city_parsed'):
        city_result = verify_city_amalgamation(parsed_address['city_parsed'], nar_cities)
        if city_result:
            result['city_verified'], result['city_confidence'] = city_result
            result['city_verification_method'] = 'amalgamation'

    # 1d. Try fuzzy match
    if not result['city_verified'] and parsed_address.get('city_parsed'):
        city_result = verify_city_fuzzy(parsed_address['city_parsed'], nar_cities_list)
        if city_result:
            result['city_verified'], result['city_confidence'] = city_result
            result['city_verification_method'] = 'fuzzy'

    # STEP 2: Validate Address (if city verified)

    if result['city_verified'] and result['city_confidence'] >= 85:
        nar_result = validate_address_in_nar(
            parsed_address.get('house_number'),
            parsed_address.get('road'),
            result['city_verified']
        )

        if nar_result:
            result['nar_found'] = True
            result['address_verified'] = f"{nar_result['house_number']} {parsed_address.get('road')}"
            result['address_confidence'] = nar_result['confidence']
            result['nar_postal_code'] = nar_result['postal_code']
            result['nar_latitude'] = nar_result['latitude']
            result['nar_longitude'] = nar_result['longitude']
        else:
            # City verified but address not in NAR
            result['address_confidence'] = result['city_confidence']

    return result
```

### Report Format
```
STANDARDIZATION REPORT - 1000 Sample Addresses
================================================

PARSING RESULTS:
- Addresses parsed: 1000 (100%)
- House number extracted: 950 (95%)
- Road extracted: 940 (94%)
- City extracted: 920 (92%)
- Postal code extracted: 450 (45%)

CITY VERIFICATION:
- Postal code lookup: 420 (42%)
- Exact match: 350 (35%)
- Amalgamation: 80 (8%)
- Fuzzy match: 50 (5%)
- NOT VERIFIED: 100 (10%)

CONFIDENCE LEVELS:
- ≥95 confidence: 420 (42%)
- 90-94 confidence: 350 (35%)
- 85-89 confidence: 130 (13%)
- <85 confidence: 100 (10%)

NAR ADDRESS VALIDATION:
- Found in NAR: 650 (65%)
- Not found (but city verified): 250 (25%)
- Not validated (city not verified): 100 (10%)

HYPHENATED ADDRESSES:
- Total hyphenated: 75
- Matched in NAR: 60 (80%)
- NOT matched: 15 (20%)
```

### Deliverable
- Complete standardization script
- Report on 1000 samples
- Sample of 50 addresses showing before/after

### Success Criteria
- City verification ≥90%
- NAR match rate ≥60% (for addresses with verified cities)
- No false positives in city matching

### Checkpoint
**STOP** - Full review of results before proceeding to production

---

## SUMMARY: Phase-by-Phase Approach

| Phase | What We Build | What We Verify | When We Stop |
|-------|---------------|----------------|--------------|
| 1 | Install libpostal | Parsing works | After 10 test parses |
| 2 | Parse transactions | Extraction quality | After 100 parses |
| 3 | Parse brand locations | Extraction quality | After 100 parses |
| 4 | Postal → city | Lookup accuracy | After 100 lookups |
| 5 | Exact city match | Match accuracy | After 100 checks |
| 6 | Amalgamation map | Mapping correctness | After review |
| 7 | Fuzzy city match | No false positives | After 100 fuzzy matches |
| 8 | Range expansion | Expansion logic | After 20 test expansions |
| 9 | NAR validation | Match rate | After 100 validations |
| 10 | Full integration | End-to-end results | After 1000 samples |

Each phase is independent and testable. We verify results before moving to the next phase.

Ready to start with Phase 1?
