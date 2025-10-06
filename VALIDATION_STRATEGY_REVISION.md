# NAR Validation Strategy - REVISION REQUIRED

**Date:** 2025-10-03
**Status:** ❌ CURRENT APPROACH FAILING - NEEDS REDESIGN

---

## Critical Issues Found

### Issue 1: Postal Code Query Too Strict ❌

**Current Approach:**
```python
# Requires BOTH address AND postal code to match
WHERE number = '3'
  AND street LIKE '%PENINSULA%'
  AND zipcode = 'P0T2E0'
```

**Result:** FAILS even though postal code is in NAR!
- P0T 2E0 → 602 addresses in MARATHON in NAR
- "3 Peninsula Road" not in NAR
- Current query returns NOTHING

**Should Be:**
```python
# Strategy 1: Query by postal code ALONE
WHERE zipcode = 'P0T2E0'
# Returns: MARATHON (from 602 addresses)

# Strategy 2: Then try to validate address exists
WHERE number = '3' AND street LIKE '%PENINSULA%' AND city = 'MARATHON'
```

### Issue 2: Hyphenated Address Ranges ❌

**Current Approach:**
```
Address: "3310 - 3350 STEELES AVE W"
Parsed number: "3310 - 3350"
Query: WHERE number = '3310 - 3350'
Result: NOT FOUND
```

**Should Be:**
```
Address: "3310 - 3350 STEELES AVE W"
Parse range: "3310 - 3350" → ["3310", "3350"]
Try first: WHERE number = '3310' → FOUND in CONCORD ✅
```

### Issue 3: NAR Coverage Gaps ❌

**Problem:** Some addresses exist in real world but not in NAR
- Google finds "3 Peninsula Road, Marathon"
- NAR doesn't have this specific address
- BUT NAR has 602 other addresses with postal code P0T 2E0 in MARATHON

**Solution:** Use postal code to infer city even when address not in NAR

---

## Revised Strategy (Postal Code First!)

### New Multi-Level Strategy:

```
IF postal_code present:

    LEVEL 1: Postal Code → City (Confidence: 95%)
    ─────────────────────────────────────────────────
    Query NAR by postal code ONLY

    SELECT city, COUNT(*) as count
    FROM NAR
    WHERE zipcode = postal_code
    GROUP BY city
    ORDER BY count DESC
    LIMIT 1

    If found → Use this city (confidence: 95%)


    LEVEL 2: Postal Code + Address Match (Confidence: 100%)
    ──────────────────────────────────────────────────────────
    Try to find the specific address in NAR

    SELECT city, zipcode, lat, lon
    FROM NAR
    WHERE zipcode = postal_code
      AND number = street_number
      AND street LIKE street_name

    If found → Perfect match (confidence: 100%)
    If not found → Still use Level 1 city (confidence: 95%)


ELSE IF city_hint present (no postal code):

    LEVEL 3: Address + City Match (Confidence: 90%)
    ──────────────────────────────────────────────────
    SELECT city, zipcode, lat, lon
    FROM NAR
    WHERE city = city_hint
      AND number = street_number
      AND street LIKE street_name

    If found → Good match (confidence: 90%)


    LEVEL 4: Fuzzy Address Match (Confidence: 70%)
    ─────────────────────────────────────────────────
    SELECT city, zipcode, lat, lon
    FROM NAR
    WHERE number = street_number
      AND street LIKE street_name
    LIMIT 1

    If found → Fuzzy match (confidence: 70%)


ELSE:
    Not found (confidence: 0%)
```

---

## Address Preprocessing Improvements

### Handle Hyphenated Ranges:

```python
def parse_street_number(address: str) -> str:
    """
    Parse street number from address, handling ranges.

    Examples:
        "3310 - 3350 STEELES AVE W" → "3310"
        "123 Main Street" → "123"
        "123A King St" → "123A"
    """
    # Extract first token
    parts = address.strip().split(maxsplit=1)
    if not parts:
        return None

    street_number = parts[0]

    # Check for range (e.g., "3310 - 3350")
    if '-' in street_number and len(street_number) > 3:
        # Split on hyphen and take first number
        range_parts = street_number.split('-')
        street_number = range_parts[0].strip()

    return street_number
```

### Handle Prefix Text:

```python
def parse_address_with_prefix(address: str) -> str:
    """
    Remove city prefix from address.

    Examples:
        "Quinte West 178 Front St" → "178 Front St"
        "Port Hope 20 Jocelyn Street" → "20 Jocelyn Street"
    """
    # Common prefixes to remove
    # Check if first word is in city list and second word is a number
    parts = address.strip().split()

    if len(parts) >= 2:
        # Check if second part is a number
        if parts[1].replace('-', '').isdigit():
            # First part might be city name
            return ' '.join(parts[1:])

    return address
```

---

## Expected Results After Fix

### Current Results (BROKEN):
- 104 properties with postal codes
- 69 got cities from NAR (66%)
- 63 FAILED despite having postal codes (34%)

### Expected Results (FIXED):
- 104 properties with postal codes
- **~100+ should get cities** (95%+)
- Only fail if postal code invalid or not in NAR

### Why This Will Work:

**Example 1: "3 Peninsula Road, Marathon, P0T 2E0"**
- Current: NOT FOUND (address not in NAR)
- Fixed: Query P0T 2E0 → Find 602 addresses → Return MARATHON ✅

**Example 2: "3310 - 3350 STEELES AVE W, VAUGHAN"**
- Current: NOT FOUND (range format)
- Fixed: Parse "3310" → Find in NAR → Return CONCORD ✅

**Example 3: "Quinte West 178 Front St, Trenton, K8V 4N8"**
- Current: NOT FOUND (prefix text)
- Fixed: Query K8V 4N8 → Find 3 addresses → Return TRENTON ✅

---

## Implementation Plan

1. **Rewrite query_nar() method** - Use postal code first strategy
2. **Add parse_street_number()** - Handle ranges
3. **Add parse_address_with_prefix()** - Remove city prefixes
4. **Update confidence scores** - 95% for postal-only, 100% for postal+address
5. **Test on same 149 properties** - Should see 95%+ success rate
6. **Re-validate entire approach** - Get user approval before full backfill

---

## Testing Targets

After implementing fixes, we should see:

| Metric | Before | After Target |
|--------|--------|--------------|
| Properties with postal codes | 104 | 104 |
| Cities found from postal codes | 69 (66%) | **~100 (95%+)** |
| High confidence (≥90) | 48 (32%) | **~100 (67%+)** |
| Postal codes added | 47 (31%) | **~100 (67%+)** |
| Geocoding added | 48 (32%) | **~100 (67%+)** |

This is what the user expected - postal codes should give us nearly 100% accuracy!
