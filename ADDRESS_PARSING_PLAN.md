# Comprehensive Address Parsing Plan

**Date:** 2025-10-03
**Purpose:** Define a systematic approach to parse all address format variations into clean, consistent components

---

## GOAL

Transform messy raw addresses into clean, normalized components that can be:
1. Validated against NAR database
2. Geocoded accurately
3. Queried consistently

### Target Output Format:
```python
{
    'street_number': '212',           # First number only (from ranges)
    'street_name': 'WELLAND AVENUE',  # Clean street name (no number, no unit, no city)
    'unit': 'Unit 1',                 # Extracted unit (if present)
    'city': 'St. Catharines',         # Clean city (no suburb)
    'suburb': 'Scarborough',          # Extracted suburb (if present)
    'postal_code': 'L2R 2P2',         # Clean postal (spaces added)
    'address_clean': '212 WELLAND AVENUE'  # Reconstructed clean address
}
```

---

## PARSING RULES (Applied in Order)

### Rule 1: Strip Unit Numbers

**Purpose:** Remove unit/suite designations that aren't part of the base address

**Patterns to Match:**
- `#Unit 1`, `#Unit 204`
- `Unit D20`, `#Suite 113`
- `#300`, `#H`

**Regex:**
```python
UNIT_PATTERN = re.compile(r'\s+#?(Unit|Suite|Ste|Apt)\s+[A-Z0-9.]+', re.IGNORECASE)
UNIT_SHORT_PATTERN = re.compile(r'\s+#[A-Z0-9]+$', re.IGNORECASE)
```

**Examples:**
```
Input:  "973 Montréal Road #Unit 1"
Output: "973 Montréal Road"
Unit:   "Unit 1"

Input:  "338 Rossland Road East #300"
Output: "338 Rossland Road East"
Unit:   "300"

Input:  "911 Richmond Road #H"
Output: "911 Richmond Road"
Unit:   "H"
```

---

### Rule 2: Remove City Prefix

**Purpose:** Remove city name when it appears before the street number

**Patterns to Match:**
- `St. Catharines 212 Welland Avenue`
- `Niagara Falls 6380 Fallsview Boulevard`
- `Sault Ste. Marie 153 Great Northern Road`

**Logic:**
```python
def remove_city_prefix(address: str) -> str:
    """
    Remove city prefix if present.

    Pattern: City name followed by a number
    Example: "St. Catharines 212 Welland" → "212 Welland"
    """
    parts = address.strip().split()

    # Find first part that starts with a digit
    for i, part in enumerate(parts):
        if part[0].isdigit():
            # Everything before this is the city prefix
            return ' '.join(parts[i:])

    # No number found, return as-is
    return address
```

**Examples:**
```
Input:  "St. Catharines 212 Welland Avenue"
Output: "212 Welland Avenue"

Input:  "Niagara Falls 6380 Fallsview Boulevard"
Output: "6380 Fallsview Boulevard"

Input:  "212 Welland Avenue"  (no prefix)
Output: "212 Welland Avenue"  (unchanged)
```

---

### Rule 3: Parse Hyphenated Ranges

**Purpose:** Extract first number from address ranges

**Patterns to Match:**
- `251 - 255 DAVENPORT RD` (space-separated)
- `745-747 ST CLAIR ST` (no spaces)
- `41 - 47 BEACH DR`

**Logic:**
```python
def parse_street_number(address: str) -> tuple[str, str]:
    """
    Extract street number, handling ranges.

    Returns: (street_number, remaining_address)
    """
    parts = address.strip().split(maxsplit=1)
    if not parts:
        return None, address

    street_number = parts[0]
    remaining = parts[1] if len(parts) > 1 else ""

    # Handle hyphenated range
    if '-' in street_number:
        # "251-255" → "251"
        range_parts = re.split(r'\s*-\s*', street_number)
        street_number = range_parts[0].strip()

    # Handle space-separated range: "251 - 255 STREET"
    if remaining.startswith('-') or (len(parts) > 2 and parts[1] == '-'):
        # Skip the hyphen and second number
        # "251 - 255 DAVENPORT" → number="251", remaining="DAVENPORT"
        rest_parts = remaining.split(maxsplit=2)
        if len(rest_parts) >= 2:
            remaining = rest_parts[1] if len(rest_parts) > 1 else ""

    return street_number, remaining
```

**Examples:**
```
Input:  "251 - 255 DAVENPORT RD"
Output: number="251", street="DAVENPORT RD"

Input:  "745-747 ST CLAIR ST"
Output: number="745", street="ST CLAIR ST"

Input:  "123 Main Street"
Output: number="123", street="Main Street"
```

---

### Rule 4: Parse Ampersand Separators

**Purpose:** Handle addresses with `&` separator (treat like range)

**Pattern:**
- `8 & 14 FOREST AVE`

**Logic:**
```python
# Normalize & to - before parsing
address = address.replace(' & ', ' - ')
# Then apply Rule 3 (hyphenated range)
```

**Examples:**
```
Input:  "8 & 14 FOREST AVE"
Step 1: "8 - 14 FOREST AVE"  (normalize)
Step 2: number="8", street="FOREST AVE"  (parse range)
```

---

### Rule 5: Extract City from Parenthetical

**Purpose:** Separate city and suburb when city contains parentheses

**Pattern:**
- `Toronto (Scarborough)`
- `Ottawa (Gloucester)`
- `Ottawa (Nepean)`

**Logic:**
```python
def parse_city_suburb(city: str) -> tuple[str, str | None]:
    """
    Extract suburb from city field.

    Returns: (city, suburb)
    """
    if not city or '(' not in city:
        return city, None

    # "Toronto (Scarborough)" → ("Toronto", "Scarborough")
    match = re.match(r'^(.+?)\s*\((.+?)\)$', city.strip())
    if match:
        return match.group(1).strip(), match.group(2).strip()

    return city, None
```

**Examples:**
```
Input:  "Toronto (Scarborough)"
Output: city="Toronto", suburb="Scarborough"

Input:  "Ottawa (Gloucester)"
Output: city="Ottawa", suburb="Gloucester"

Input:  "Toronto"
Output: city="Toronto", suburb=None
```

---

### Rule 6: Normalize Postal Code

**Purpose:** Ensure consistent postal code format

**Patterns:**
- `L1N9L4` → `L1N 9L4` (add space)
- `L1N 9L4` → `L1N 9L4` (already correct)
- `l1n 9l4` → `L1N 9L4` (uppercase)

**Logic:**
```python
def normalize_postal_code(postal: str | None) -> str | None:
    """
    Normalize Canadian postal code to format: A1A 1A1
    """
    if not postal:
        return None

    # Remove all spaces and uppercase
    clean = postal.strip().upper().replace(' ', '')

    # Must be exactly 6 characters
    if len(clean) != 6:
        return postal  # Return original if invalid

    # Insert space after 3rd character
    return f"{clean[:3]} {clean[3:]}"
```

**Examples:**
```
Input:  "L1N9L4"
Output: "L1N 9L4"

Input:  "M1E2P8"
Output: "M1E 2P8"

Input:  "K1B 1A5"
Output: "K1B 1A5"  (unchanged)
```

---

### Rule 7: Normalize Street Name

**Purpose:** Standardize common abbreviations in street names

**Patterns:**
- `STREET` → `ST`
- `AVENUE` → `AVE`
- `ROAD` → `RD`
- `BOULEVARD` → `BLVD`
- `DRIVE` → `DR`

**Logic:**
```python
def normalize_street_name(street: str) -> str:
    """
    Normalize street suffixes to standard abbreviations.
    """
    if not street:
        return street

    street_upper = street.upper().strip()

    abbreviations = {
        ' STREET': ' ST',
        ' AVENUE': ' AVE',
        ' ROAD': ' RD',
        ' BOULEVARD': ' BLVD',
        ' DRIVE': ' DR',
        ' LANE': ' LN',
        ' COURT': ' CT',
        ' CRESCENT': ' CRES',
        ' PLACE': ' PL',
        ' CIRCLE': ' CIR',
        ' PARKWAY': ' PKWY',
        ' HIGHWAY': ' HWY'
    }

    for full, abbr in abbreviations.items():
        if street_upper.endswith(full):
            street_upper = street_upper[:-len(full)] + abbr
            break

    return street_upper
```

**Examples:**
```
Input:  "DAVENPORT ROAD"
Output: "DAVENPORT RD"

Input:  "WILSON AVENUE"
Output: "WILSON AVE"

Input:  "MAIN ST"
Output: "MAIN ST"  (already abbreviated)
```

---

## COMPLETE PARSING PIPELINE

### Step-by-Step Process:

```python
def parse_address(
    address_line1: str,
    city: str | None = None,
    postal_code: str | None = None
) -> dict:
    """
    Parse raw address into clean components.

    Applies all rules in order:
    1. Strip unit numbers
    2. Remove city prefix
    3. Parse hyphenated ranges
    4. Parse ampersand separators
    5. Extract city/suburb
    6. Normalize postal code
    7. Normalize street name
    """

    # Start with raw address
    address = address_line1.strip() if address_line1 else ""

    # Rule 1: Strip unit numbers
    unit = None
    match = UNIT_PATTERN.search(address)
    if match:
        unit = match.group(0).strip()
        address = UNIT_PATTERN.sub('', address).strip()
    else:
        match = UNIT_SHORT_PATTERN.search(address)
        if match:
            unit = match.group(0).strip()
            address = UNIT_SHORT_PATTERN.sub('', address).strip()

    # Rule 2: Remove city prefix
    address = remove_city_prefix(address)

    # Rule 4: Normalize ampersand to hyphen
    address = address.replace(' & ', ' - ')

    # Rule 3: Parse street number (handles ranges)
    street_number, street_name = parse_street_number(address)

    # Rule 7: Normalize street name
    street_name = normalize_street_name(street_name)

    # Rule 5: Parse city/suburb
    city_clean, suburb = parse_city_suburb(city) if city else (None, None)

    # Rule 6: Normalize postal code
    postal_clean = normalize_postal_code(postal_code)

    # Reconstruct clean address
    address_clean = f"{street_number} {street_name}".strip() if street_number and street_name else address

    return {
        'street_number': street_number,
        'street_name': street_name,
        'unit': unit,
        'city': city_clean,
        'suburb': suburb,
        'postal_code': postal_clean,
        'address_clean': address_clean
    }
```

---

## EXAMPLES: Full Pipeline

### Example 1: Brand Location with City Prefix and Unit
```python
Input:
  address_line1 = "St. Catharines 212 Welland Avenue #Unit 5"
  city = "St. Catharines"
  postal_code = "L2R2P2"

Processing:
  Rule 1 (Strip unit):     "St. Catharines 212 Welland Avenue"  (unit="Unit 5")
  Rule 2 (City prefix):    "212 Welland Avenue"
  Rule 3 (Parse number):   number="212", street="Welland Avenue"
  Rule 7 (Normalize):      street="WELLAND AVE"
  Rule 5 (City/suburb):    city="St. Catharines", suburb=None
  Rule 6 (Postal):         postal="L2R 2P2"

Output:
  {
    'street_number': '212',
    'street_name': 'WELLAND AVE',
    'unit': 'Unit 5',
    'city': 'St. Catharines',
    'suburb': None,
    'postal_code': 'L2R 2P2',
    'address_clean': '212 WELLAND AVE'
  }
```

### Example 2: Realtrack with Hyphenated Range
```python
Input:
  address_line1 = "251 - 255 DAVENPORT RD"
  city = "Toronto"
  postal_code = None

Processing:
  Rule 1 (Strip unit):     "251 - 255 DAVENPORT RD"  (no unit)
  Rule 2 (City prefix):    "251 - 255 DAVENPORT RD"  (no prefix)
  Rule 3 (Parse number):   number="251", street="DAVENPORT RD"
  Rule 7 (Normalize):      street="DAVENPORT RD"  (already abbrev)
  Rule 5 (City/suburb):    city="Toronto", suburb=None
  Rule 6 (Postal):         postal=None

Output:
  {
    'street_number': '251',
    'street_name': 'DAVENPORT RD',
    'unit': None,
    'city': 'Toronto',
    'suburb': None,
    'postal_code': None,
    'address_clean': '251 DAVENPORT RD'
  }
```

### Example 3: Brand Location with City Parenthetical
```python
Input:
  address_line1 = "4679 Kingston Rd"
  city = "Toronto (Scarborough)"
  postal_code = "M1E2P8"

Processing:
  Rule 1 (Strip unit):     "4679 Kingston Rd"  (no unit)
  Rule 2 (City prefix):    "4679 Kingston Rd"  (no prefix)
  Rule 3 (Parse number):   number="4679", street="Kingston Rd"
  Rule 7 (Normalize):      street="KINGSTON RD"
  Rule 5 (City/suburb):    city="Toronto", suburb="Scarborough"
  Rule 6 (Postal):         postal="M1E 2P8"

Output:
  {
    'street_number': '4679',
    'street_name': 'KINGSTON RD',
    'unit': None,
    'city': 'Toronto',
    'suburb': 'Scarborough',
    'postal_code': 'M1E 2P8',
    'address_clean': '4679 KINGSTON RD'
  }
```

### Example 4: Realtrack with Ampersand
```python
Input:
  address_line1 = "8 & 14 FOREST AVE"
  city = "Hamilton"
  postal_code = None

Processing:
  Rule 1 (Strip unit):     "8 & 14 FOREST AVE"  (no unit)
  Rule 2 (City prefix):    "8 & 14 FOREST AVE"  (no prefix)
  Rule 4 (Ampersand):      "8 - 14 FOREST AVE"
  Rule 3 (Parse number):   number="8", street="FOREST AVE"
  Rule 7 (Normalize):      street="FOREST AVE"  (already abbrev)
  Rule 5 (City/suburb):    city="Hamilton", suburb=None
  Rule 6 (Postal):         postal=None

Output:
  {
    'street_number': '8',
    'street_name': 'FOREST AVE',
    'unit': None,
    'city': 'Hamilton',
    'suburb': None,
    'postal_code': None,
    'address_clean': '8 FOREST AVE'
  }
```

---

## INTEGRATION WITH EXISTING PIPELINE

### Current Pipeline (Broken):
```
Raw Scraper → properties table → standardize_properties.py → NAR validation
               (messy data)       (tries to canonicalize)      (fails!)
```

### Proposed Pipeline (Fixed):
```
Raw Scraper → properties table → PARSE ADDRESS → Store clean components → NAR validation
               (messy data)       (NEW STEP!)     (clean data!)           (succeeds!)
```

### Where to Implement:

**Option 1: At Import Time** (Recommended)
- Modify `realtrack_ingest.py` to call `parse_address()` before storing
- Modify brand locations import to call `parse_address()` before storing
- Store parsed components in new columns

**Option 2: As Migration Script**
- Create `scripts/fixes/parse_all_addresses.py`
- Run once to clean existing data
- Then apply at import time for new data

**Option 3: In Standardization Script**
- Modify `standardize_properties.py` to parse before canonicalizing
- Run as part of existing standardization process

---

## RECOMMENDED NEW SCHEMA

### Add to `properties` table:
```sql
ALTER TABLE properties
ADD COLUMN street_number VARCHAR,
ADD COLUMN street_name VARCHAR,
ADD COLUMN unit VARCHAR,
ADD COLUMN suburb VARCHAR;
```

### Benefits:
1. Clean components stored for fast querying
2. Original data preserved in `address_line1` (for audit)
3. NAR validation can use clean `street_number` + `street_name`
4. Geocoding can use clean `address_clean`

---

## SUCCESS CRITERIA

After implementing this parsing plan, we should see:

1. **100% address parsing success** (all addresses get street_number + street_name extracted)
2. **95%+ NAR match rate for addresses with postal codes** (postal-first strategy)
3. **85%+ NAR match rate for addresses without postal codes** (clean address matching)
4. **0% data corruption** (original data preserved, only cleaned copies added)

---

## NEXT STEPS

1. Review this plan with user
2. Get approval on:
   - Schema changes (new columns)
   - Where to implement (import time vs migration vs standardization)
   - Testing strategy
3. Implement parser as module: `common/address_parser.py`
4. Write comprehensive tests
5. Run on sample of 1000 properties
6. Review results
7. Run full migration if successful
8. Update NAR validator to use clean components
