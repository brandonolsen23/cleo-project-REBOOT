# CSV Report Bug - Explanation

**Date:** 2025-10-03
**Issue:** First CSV report was misleading
**Status:** ✅ FIXED - Database was never corrupted

---

## What Happened

The original CSV report (`validation_report_20251003_152544.csv`) showed that 80 cities were "blanked" after validation, which looked like a disaster. **However, this was just a misleading CSV report - the database was never corrupted.**

### The Bug in the CSV

**Original CSV showed:**
- Column "City (After)" = `q.city_after` (what NAR returned, can be None)
- This made it look like cities were being blanked!

**Reality:**
- The actual city in the properties table (`p.city`) was preserved
- Cities were ONLY updated when confidence ≥90
- When NAR didn't find an address (confidence=0), the original city stayed intact

### Verification

Checked the database directly:
```sql
SELECT COUNT(*)
FROM properties p
JOIN nar_validation_queue q ON p.id = q.property_id
WHERE q.status = 'completed'
  AND q.city_before IS NOT NULL
  AND p.city IS NULL
```

**Result: 0 properties had their city blanked**

---

## Corrected Statistics

### Original (Misleading) Report:
- City updated: 132 (88.6%) ❌ WRONG
- This counted every property where q.city_after was different from city_before
- But q.city_after is None when NAR doesn't find the address!

### Corrected Report (`validation_report_CORRECTED.csv`):
- **City updated: 6 (4.0%)** ✅ CORRECT
- **Postal code updated: 47 (31.5%)** ✅ CORRECT
- **Geocoding updated: 48 (32.2%)** ✅ CORRECT

### Why Only 6 Cities Updated?

Of the 149 properties validated:
- 48 had high confidence (≥90)
- Of those 48:
  - 42 already had the correct city (no update needed)
  - **6 needed city corrections** (these were updated)

This is GOOD - it means:
1. Most properties already had correct cities
2. We only update when necessary
3. Low-confidence matches are left unchanged (safe!)

---

## Examples from Corrected CSV

### Example 1: Not Found in NAR (City Preserved)
```
Address: 3 Peninsula Road, Marathon, P0T 2E0
BEFORE: Marathon
NAR RESULT: (not found)
FINAL: Marathon ✅ (preserved)
Confidence: 0%
```

### Example 2: Found in NAR, High Confidence (Updated)
```
Address: 9025 TORBRAM RD, BRAMPTON
BEFORE: BRAMPTON
NAR RESULT: BRAMPTON
FINAL: BRAMPTON ✅ (confirmed)
Postal added: L6S3L2
Geocoding added: 43.73, -79.73
Confidence: 90%
```

### Example 3: Found in NAR, Low Confidence (Preserved)
```
Address: 25 Toronto Street, Colborne
BEFORE: Colborne
NAR RESULT: TORONTO (fuzzy match - wrong!)
FINAL: Colborne ✅ (preserved, confidence too low)
Confidence: 70%
```

---

## The Fix

Updated the CSV generation script to show:

| Section | Columns |
|---------|---------|
| **BEFORE VALIDATION** | City (Before), Postal Code (Before) |
| **NAR RESULT** | City from NAR, Postal from NAR, Confidence, Found in NAR |
| **AFTER VALIDATION (FINAL)** | City (Final in DB), Postal Code (Final in DB), Lat, Lon |

Now it's crystal clear:
- What the property had before
- What NAR returned (can be None)
- What's actually in the database now (the final state)

---

## Key Takeaway

**The validation system was working correctly all along!**

✅ Cities are ONLY updated when confidence ≥90
✅ Original cities are preserved when NAR doesn't find the address
✅ All raw data is safe
✅ The misleading CSV has been corrected

---

## Files

- ❌ `validation_report_20251003_152544.csv` - Original (misleading)
- ✅ `validation_report_CORRECTED.csv` - Corrected (accurate)
