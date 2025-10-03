# Address Normalization Improvement Plan

**Date:** 2025-10-02
**Status:** CRITICAL - Address matching currently broken

---

## Executive Summary

**Current State:** Address normalization is fundamentally broken, preventing proper matching of brand locations with transaction properties.

**Root Cause:** Scrapers ingest raw, unnormalized address data directly into the `properties` table without validation or parsing.

**Impact:**
- Unit numbers appearing in city field ("Unit #24", "Unit 1")
- Full street addresses in city field ("345 King Street West")
- Sub-municipality variations causing duplicates ("Toronto (Scarborough)", "Toronto (York)")
- Address matching failing due to inconsistent city values
- 100% brand location match rate is MISLEADING - it just means every brand_location has *a* property_id, not necessarily the *correct* one

---

## Problems Identified

### 1. City Field Data Quality Issues

**Examples from production data:**

| What's in "City" field | What it SHOULD be | Issue Type |
|---|---|---|
| `Unit #24` | Brampton | Unit number |
| `Unit 1` | Stouffville | Unit number |
| `Suite 105` | Mississauga | Suite number |
| `345 King Street West` | Toronto | Full address |
| `5800 MAVIS RD` | Mississauga | Street address |
| `Toronto (Scarborough)` | Toronto | Sub-municipality |
| `Hamilton (Ancaster)` | Hamilton | Sub-municipality |
| `Halton Hills (Georgetown)` | Halton Hills | Sub-municipality |
| `Innisfil (Alcona)` | Innisfil | Sub-municipality |

**Impact:**
- 199 unique "city" values in just 1,000 properties sampled
- Multiple variations of same city prevent aggregation
- `address_hash` includes wrong city, so matching fails
- Users see garbage data in UI filters

### 2. Address Parsing Failures

**Current process:**
```python
# RealTrack ingestion - NO VALIDATION
addr = rec.get("Address") or ""  # Takes raw data as-is
city = rec.get("City") or ""     # No parsing or validation!
```

**What's happening:**
1. RealTrack scraper gets JSON like: `{"Address": "123 Main St", "City": "Unit 5"}`
2. Data is inserted directly into `properties` table
3. `address_canonical` is built from wrong inputs: `"123 MAIN ST, UNIT 5, ON, CA"`
4. `address_hash` is computed from garbage data
5. Future brand locations fail to match because hash doesn't align

### 3. Normalization Logic Gaps

**Current normalization (canonical.py):**
- Only uppercases and removes punctuation
- Does NOT validate that city is actually a city name
- Does NOT parse/extract city from full address strings
- Does NOT handle sub-municipality variations
- Does NOT extract unit numbers to separate field

**Result:** "Garbage in, garbage out"

---

## Analysis Results

### City Quality Scan (1,000 properties sample)

```
Total properties analyzed: 1,000
Unique city values: 199 (should be ~60 for ON)

Issues Found:
- Unit numbers in city field: 44 properties
- Full addresses in city field: Unknown (need deeper scan)
- Sub-municipality variations: Minimal in sample, but screenshots show many more
- HTML entities: 1 (Orléans)
```

### Address Matching Scan

```
Brand Locations: 11,913 total
- 100% have property_id assigned ✓
- But are they matched to the CORRECT property? Unknown ⚠️

Properties: 16,110 total
- 100% have address_canonical ✓
- 100% have address_hash ✓
- 68.9% have geocoding (lat/long)
- Only 6,015 have transactions linked

Property-Brand Links: 12,206 links
- Only 978 unique properties have brands (in 10k sample)
- Suggests many brand_locations matched to SAME property incorrectly?
```

---

## Recommended Solution

### Phase 1: Fix Existing Data (URGENT)

#### Step 1.1: Parse City from `address_canonical`

Many properties already have correct city in `address_canonical`. Extract it:

```python
# For properties where city field is wrong:
# address_canonical = "123 MAIN ST, UNIT 5, BRAMPTON, CA"
# Parse and update city = "BRAMPTON"
```

**Script:** `scripts/fixes/fix_city_from_canonical.py`

**Impact:** Fixes ~80% of bad city data immediately

#### Step 1.2: Use Geocoding API for Remaining

For properties where canonical is also wrong, use geocoding:

```python
# Send full address to Google/Mapbox Geocoding API
# Extract city from structured response
```

**Cost:** ~$0.005 per address × ~3,000 addresses = $15

#### Step 1.3: Re-compute address_hash

After fixing city fields:

```python
# Recalculate address_hash for all properties
UPDATE properties
SET address_hash = hash_canonical_address(address_line1, city, province, country)
```

**Impact:** Enables correct matching going forward

### Phase 2: Fix Ingestion Pipeline (CRITICAL)

#### Step 2.1: Add Address Parser

Create robust parser that:
1. Extracts street number, street name, unit from address string
2. Validates city is a real city name
3. Handles amalgamated cities (Toronto, Hamilton, Ottawa)
4. Removes sub-municipality suffixes
5. Extracts unit/suite to separate field

**New module:** `common/address_parser.py`

```python
def parse_canadian_address(address: str, city: str, province: str) -> ParsedAddress:
    """
    Parse and validate Canadian address components.

    Returns:
        ParsedAddress with:
        - street_number
        - street_name
        - unit_number (extracted from address OR city field)
        - city (validated and normalized)
        - province
        - warnings (list of issues found)
    """
```

#### Step 2.2: Update Ingestion Scripts

Modify all scrapers to use parser:

```python
# Before
addr = rec.get("Address") or ""
city = rec.get("City") or ""

# After
parsed = parse_canadian_address(
    address=rec.get("Address") or "",
    city=rec.get("City") or "",
    province="ON"
)

if parsed.warnings:
    log_warning(f"Address parse issues: {parsed.warnings}")

# Use validated fields
address_line1 = parsed.street_address
city = parsed.city  # Guaranteed to be valid city name
unit = parsed.unit_number
```

**Files to update:**
- `scripts/scraper/realtrack_ingest.py`
- Any other brand location scrapers

#### Step 2.3: Add Data Validation Layer

Before inserting into `properties`, validate:

```python
VALID_ON_CITIES = {
    "TORONTO", "OTTAWA", "MISSISSAUGA", "BRAMPTON", "HAMILTON",
    "LONDON", "MARKHAM", "VAUGHAN", "KITCHENER", "WINDSOR",
    # ... (load from reference list)
}

def validate_property_data(data: dict) -> ValidationResult:
    errors = []

    # Check city is valid
    if data["city"] not in VALID_ON_CITIES:
        errors.append(f"Invalid city: {data['city']}")

    # Check city doesn't contain numbers (except Orléans)
    if re.search(r'\d', data["city"]) and "ORLEANS" not in data["city"]:
        errors.append(f"City contains digits: {data['city']}")

    # Check city doesn't contain unit keywords
    if re.search(r'\b(unit|suite|#)\b', data["city"], re.I):
        errors.append(f"City contains unit/suite: {data['city']}")

    return ValidationResult(valid=len(errors)==0, errors=errors)
```

### Phase 3: Improve Matching Algorithm

#### Step 3.1: Multi-Pass Matching

Instead of single `address_hash` lookup:

```python
def find_matching_property(address, city, province):
    # Pass 1: Exact hash match
    match = find_by_hash(address, city, province)
    if match:
        return match

    # Pass 2: Fuzzy city match (handle Toronto variations)
    normalized_city = normalize_city(city)  # "Toronto (Scarborough)" -> "Toronto"
    match = find_by_hash(address, normalized_city, province)
    if match:
        return match

    # Pass 3: Geocoding proximity match
    if lat and lon:
        match = find_by_proximity(lat, lon, radius_meters=100)
        if match:
            return match

    # No match found - create new property
    return create_new_property(address, city, province)
```

#### Step 3.2: Toronto/Hamilton Special Handling

```python
AMALGAMATED_CITIES = {
    "SCARBOROUGH": "TORONTO",
    "ETOBICOKE": "TORONTO",
    "NORTH YORK": "TORONTO",
    "YORK": "TORONTO",
    "EAST YORK": "TORONTO",
    "ANCASTER": "HAMILTON",
    "DUNDAS": "HAMILTON",
    "FLAMBOROUGH": "HAMILTON",
    "STONEY CREEK": "HAMILTON",
    # ...
}

def normalize_city(city: str) -> str:
    """Convert old municipality names to current amalgamated city."""
    city_upper = city.upper()

    # Remove parenthetical suffixes
    base_city = re.sub(r'\s*\([^)]*\)', '', city_upper).strip()

    # Map to amalgamated city
    return AMALGAMATED_CITIES.get(base_city, base_city)
```

---

## Implementation Plan

### Week 1: Emergency Fixes
- [ ] Day 1-2: Create `fix_city_from_canonical.py` script
- [ ] Day 2-3: Run on all properties, validate results
- [ ] Day 3-4: Re-compute address_hash for all properties
- [ ] Day 4-5: Test matching improvements, measure success rate

### Week 2: Parser Development
- [ ] Day 1-2: Build `address_parser.py` with unit tests
- [ ] Day 3: Add city validation with reference list
- [ ] Day 4: Add amalgamated city handling
- [ ] Day 5: Integration testing with sample data

### Week 3: Ingestion Updates
- [ ] Day 1-2: Update `realtrack_ingest.py` to use parser
- [ ] Day 2-3: Update other scrapers
- [ ] Day 3-4: Add validation layer before database inserts
- [ ] Day 4-5: Deploy and monitor for errors

### Week 4: Matching Improvements
- [ ] Day 1-2: Implement multi-pass matching
- [ ] Day 2-3: Add geocoding fallback
- [ ] Day 3-4: Backfill any remaining unmatched locations
- [ ] Day 5: Final validation and metrics

---

## Success Metrics

### Before (Current State)
- 199 unique city values in 1,000 properties
- ~44 properties with unit numbers in city field
- Unknown % of incorrect brand-property matches
- Users see garbage data in filters

### After (Target State)
- ~60 unique city values (actual ON cities)
- 0 properties with unit/suite in city field
- >95% brand locations matched to correct property
- Clean, usable filter dropdowns
- All properties have valid, consistent city names

---

## Testing Strategy

### 1. Unit Tests
- Test address parser with known good/bad inputs
- Test city normalization (Toronto variations)
- Test validation rules

### 2. Integration Tests
- Run parser on 1,000 random RealTrack records
- Verify no regressions in matching
- Check address_hash stability

### 3. Data Quality Tests
```sql
-- No unit numbers in city
SELECT COUNT(*) FROM properties
WHERE city ~* '\b(unit|suite|#\d+)\b';
-- Expected: 0

-- All cities in valid list
SELECT DISTINCT city FROM properties
WHERE province = 'ON' AND city NOT IN (SELECT name FROM valid_cities);
-- Expected: 0 rows

-- No full addresses in city
SELECT COUNT(*) FROM properties
WHERE city ~* '(street|road|avenue|blvd|drive)';
-- Expected: 0
```

---

## Risk Assessment

### High Risk
- **Data loss**: Incorrect parsing could corrupt existing data
  - **Mitigation**: Backup database before fixes, extensive testing
- **Breaking changes**: New matching logic could orphan existing links
  - **Mitigation**: Phased rollout, validation scripts

### Medium Risk
- **Performance**: Geocoding API costs and latency
  - **Mitigation**: Cache results, batch requests
- **Edge cases**: Unusual addresses might not parse correctly
  - **Mitigation**: Manual review queue for failed parses

### Low Risk
- **User confusion**: City names changing in UI
  - **Mitigation**: Communicate changes, provide mapping

---

## Cost Estimate

### Development Time
- Phase 1 (Emergency fixes): 40 hours
- Phase 2 (Parser + ingestion): 60 hours
- Phase 3 (Matching improvements): 40 hours
- Testing + validation: 20 hours
- **Total**: ~160 hours (~4 weeks for 1 developer)

### Infrastructure Costs
- Geocoding API: ~$15-50 for one-time cleanup
- Additional database storage: Negligible
- **Total**: <$100

---

## Next Steps

1. **Approve this plan** - Review and get stakeholder buy-in
2. **Backup database** - Full snapshot before any fixes
3. **Start Week 1** - Emergency city field fixes
4. **Daily standups** - Track progress, adjust as needed

---

## Appendix: Sample Data

### Example Bad Data

```json
{
  "id": "a2af38b7-570e-42b3-8b4f-e4b53d64e23a",
  "address_line1": "9025 Airport Road",
  "city": "Unit 1",  // WRONG - should be "Brampton"
  "address_canonical": "9025 AIRPORT ROAD, UNIT 1, BRAMPTON, CA",  // City is here!
  "address_hash": "abc123..."  // Computed from wrong city
}
```

### Example Good Data (Target)

```json
{
  "id": "a2af38b7-570e-42b3-8b4f-e4b53d64e23a",
  "address_line1": "9025 Airport Road",
  "city": "Brampton",  // CORRECT
  "unit_number": "1",  // Extracted to separate field
  "address_canonical": "9025 AIRPORT ROAD, BRAMPTON, ON, CA",
  "address_hash": "xyz789..."  // Computed from correct city
}
```
