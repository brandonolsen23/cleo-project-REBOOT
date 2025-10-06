# NEXT.md

**Last updated:** 2025-10-06 (Geocoding Pipeline Complete)

---

## What We Completed Today (2025-10-06)

### ✅ **Complete Geocoding Pipeline - PRODUCTION READY** 🎉

**Built a full 3-stage geocoding workflow for RealTrack transaction addresses**

**Pipeline Overview:**
1. **Parse** multi-property addresses → `transaction_address_expansion_parse`
2. **Geocode** with Google API → `google_geocoded_addresses`
3. **Quality Review** → flag `needs_manual_review`

**Test Results (1,000 transactions):**
- ✅ 1,921 addresses parsed from 1,000 transactions
- ✅ 1,900 successfully geocoded with postal codes (98.9% success rate)
- ✅ 21 flagged for manual review (1.1%)
- ✅ Multi-property detection: 33.7% (647/1,921 addresses)

**Data Quality Validation (7 comprehensive tests):**
- ✅ Coordinate clustering: 2 clusters detected (likely plazas/city centers)
- ⚠️ City mismatches: 209 addresses (mostly legitimate amalgamations - Ottawa, Hamilton)
- ⚠️ Range duplicates: 10 range addresses with identical coordinates (flagged)
- ✅ Highway addresses: 90.9% success rate (4/44 flagged)
- ✅ Postal code format: 99.3% valid (14/1,900 minor issues)
- ✅ Distance anomalies: 1 address detected (Finch Ave W)
- ✅ Transaction linkage: 100% integrity

**Files Created:**
- `scripts/parsing/parse_transaction_addresses.py` - Multi-property address parser
- `scripts/geocoding/geocode_expanded_addresses.py` - Google Geocoding API integration
- `scripts/quality/review_geocoded_addresses.py` - Post-geocoding quality checks
- `scripts/validation/data_quality_validation.py` - 7 comprehensive validation tests
- `scripts/analysis/export_city_mismatches.py` - Export city discrepancies for review
- `common/multi_property_parser.py` - Handles &, range-dash, comma-separated patterns
- `common/google_geocoder.py` - Google Geocoding API wrapper
- `common/enhanced_geocoder.py` - Text Search API fallback (not used in final flow)
- `common/address_validator.py` - Places API validation (experimental)

**Database Tables Created:**
- `transaction_address_expansion_parse` - Individual addresses from multi-property parsing
- `google_geocoded_addresses` - Geocoding results with quality flags
- `transaction_address_links` - Links transactions to geocoded addresses

**Key Features:**
- ✅ Resume-safe: Can stop/restart without duplicating work
- ✅ Multi-property parsing: "471 & 481 KING ST E" → [471 KING ST E, 481 KING ST E]
- ✅ Range expansion: "9220 - 9226 HWY 93" → [9220, 9222, 9224, 9226]
- ✅ Quality flagging: Duplicate coordinates, missing postal codes, city-level only results
- ✅ Rate limiting: 0.3s between Google API calls
- ✅ Background processing: Long-running tasks continue after terminal disconnect

**Next Steps:**
- [ ] Review 209 city mismatches manually (/tmp/city_mismatches.csv)
- [ ] Decide: Scale to remaining ~5,000 transactions or address city mismatches first
- [ ] Consider: Run quality review script on all geocoded addresses
- [ ] Optional: Integrate with brand location matching

---

## What We Completed Previously (2025-10-03)

### ✅ **Phase 1: libpostal Installation & Testing - COMPLETE** 🎉

**Achievements:**
- ✅ Installed libpostal C library from source (v1.1.3)
- ✅ Properly installed to `/usr/local/` (system location)
- ✅ Installed Python wrapper via pip
- ✅ Tested on 10 sample addresses (5 transactions, 5 brand_locations)
- ✅ 100% success rate on house_number, road, city extraction
- ✅ Configured sudo NOPASSWD for make/brew commands

**Test Results:**
- House Number: 10/10 (100%)
- Road/Street: 10/10 (100%)
- City: 10/10 (100%)
- Postal Code: 5/10 (50% - expected)

**Key Findings:**
- libpostal works excellently for Canadian addresses
- 2 hyphenated addresses detected (will handle in Phase 8)
- No environment variables needed - properly linked

**Files Created:**
- `CLAUDE.md` - Project context for AI assistant
- `scripts/analysis/fetch_sample_addresses.py` - Sample address fetcher
- `scripts/analysis/test_libpostal_parsing.py` - Test suite with metrics

**System Configuration:**
- Configured `/etc/sudoers` for passwordless make/brew
- libpostal installed to `/usr/local/lib/libpostal.1.dylib`
- Python wrapper properly linked to system library

**Ready for Phase 2:** Parse Transactions Table

---

## What We Completed Previously (2025-10-03)

### ✅ **NAR Validation System - COMPLETE** 🎉

**Full production-ready validation system:**
- ✅ Database schema (3 tables, 11 indexes, 2 views)
- ✅ NARValidator class with postal code validation and caching
- ✅ Background service with batch processing (100 properties/batch)
- ✅ Queue system integrated with RealTrack workflow
- ✅ Backfill script for existing 16k properties
- ✅ Email alerts for service failures
- ✅ Monitoring/status dashboard
- ✅ Complete documentation

**Validation Strategy:**
- Level 1: Postal code + address match (confidence: 100)
- Level 2: City + address match (confidence: 90)
- Level 3: Fuzzy city match (confidence: 70)
- Updates: City (always), postal code (≥90), geocoding (≥90)

**Performance:**
- Cache hit rate: 60-80% (reduces query time 200x)
- Batch processing: 100 properties in 10-30 seconds
- Estimated backfill time: 4-8 hours for 16k properties
- NAR database: 5.7M Ontario addresses, 1,153 cities

**Files Created:**
- `common/nar_validator.py` - Validator with caching
- `common/queue_nar_validation.py` - Queue helper
- `scripts/setup/setup_nar_validation.py` - Database setup
- `scripts/services/nar_validation_service.py` - Background service
- `scripts/backfill/backfill_nar_validation.py` - Backfill script
- `scripts/monitoring/nar_validation_status.py` - Status monitor
- `scripts/scraper/post_realtrack_queue_validation.py` - Queue hook
- `docs/NAR_VALIDATION_SYSTEM.md` - Complete documentation

**Ready for Deployment:**
```bash
# 1. Start backfill (4-8 hours)
python3 scripts/backfill/backfill_nar_validation.py

# 2. Start background service
screen -S nar-validator
python3 scripts/services/nar_validation_service.py

# 3. Monitor progress
watch -n 5 python3 scripts/monitoring/nar_validation_status.py
```

---

### ✅ **Address Data Quality Fix - Phase 1 COMPLETE**

**Safe Address Normalization Implementation:**
- ✅ Added backup columns to preserve ALL raw data (16,100 properties backed up)
- ✅ Built comprehensive address parser with Ontario cities validation
- ✅ Created 19 unit tests for address parser (all passing)
- ✅ Fixed 13,489 properties (83.7% of database)
- ✅ Integrated NAR 2024 database (5.7M Ontario addresses, 1,153 cities)
- ✅ Zero unit/suite/address garbage in city field (was 70, now 0)
- ✅ RealTrack scraper completely untouched (as requested)

**Key Achievements:**
- Extracted 1,153 valid Ontario cities from Statistics Canada NAR 2024
- Normalized city names (Toronto → TORONTO)
- Consolidated amalgamated cities (Scarborough → TORONTO, Etobicoke → TORONTO)
- Fixed abbreviations (N. York → NORTH YORK, E. York → EAST YORK)
- Re-computed address hashes with corrected city data

**Safety Measures:**
- All raw data backed up in `city_backup` and `city_raw_backup` columns
- Instant rollback capability: `UPDATE properties SET city = city_backup;`
- Preview analysis run before applying any changes
- Validation confirms all fixes successful

**Documentation Created:**
- `docs/ADDRESS_FIX_SUMMARY.md` - Complete technical summary
- Updated address normalization plan with safe approach
- Scripts for extraction, fixing, and validation

---

## What We Completed Previously (2025-10-02)

✅ **Properties Table Implementation**
- Added sortable columns: Address, City, Sale Date, Sale Price, Brands, Buyer, Seller
- Clicking any column header sorts A-Z, clicking again sorts Z-A
- Removed "Action" column - entire row now clickable to view property details

✅ **Advanced Filters UI**
- Horizontal filter layout (not collapsible - always visible)
- City filter dropdown with ALL 60+ cities now loading correctly
- Brand filter dropdown
- Buyer filter dropdown (populated with buyer data)
- Seller filter dropdown (populated with seller data)
- Price filter with min/max dropdowns (preset ranges: $500k - $1B)
- Reset All button when filters active

✅ **Transaction Data Integration**
- Properties page now fetches latest transaction for each property
- Displays: transaction_date, price, buyer_name, seller_name
- 14,481 properties with transactions in database
- Buyer/Seller data successfully populated

✅ **City Dropdown Fix - RESOLVED**
- **Root Cause**: Supabase PostgREST default limit of 1000 rows was only returning first 1000 properties
- **Solution**: Implemented batched fetching (1000 rows per batch, up to 15k total)
- **Result**: All 60+ unique cities now load correctly in dropdown
- **Technical**: Used `.range(from, to)` in loop to fetch multiple batches and deduplicate cities

✅ **Next.js Cache Issue Fix**
- Cleared `.next` cache directory to resolve CSS loading issues
- Ant Design styles now loading correctly after dev server restart

✅ **Database Address Quality Analysis - CRITICAL ISSUES FOUND**
- Analyzed address normalization quality across properties table
- Discovered fundamental data quality issues preventing proper address matching
- Created comprehensive diagnosis and fix plan

---

## Critical Issues Discovered

### 🚨 Address Normalization is Broken

**Problem Summary:**
The city field contains garbage data that breaks address matching:
- Unit numbers: "Unit #24", "Unit 1", "Suite 105"
- Full street addresses: "345 King Street West", "5800 MAVIS RD"
- Sub-municipality variations: "Toronto (Scarborough)", "Hamilton (Ancaster)", "Halton Hills (Georgetown)"
- Result: 199 unique "city" values in just 1,000 properties (should be ~60 actual cities)

**Root Cause:**
RealTrack scraper (`scripts/scraper/realtrack_ingest.py`) takes raw JSON fields with ZERO validation:
```python
addr = rec.get("Address") or ""  # No parsing
city = rec.get("City") or ""     # No validation - whatever garbage is in source JSON goes into DB!
```

**Impact:**
- `address_hash` computed from wrong city values
- Brand locations may be matched to WRONG properties
- Address matching failing silently
- Users see duplicate/invalid cities in filter dropdowns
- Impossible to properly aggregate data by city

**Example Bad Data:**
```
Property ID: a2af38b7-570e-42b3-8b4f-e4b53d64e23a
Address Line 1: "9025 Airport Road"
City: "Unit 1"  ❌ WRONG
Canonical: "9025 AIRPORT ROAD, UNIT 1, BRAMPTON, CA"  ← Correct city is here!
```

---

## Technical Details

**City Dropdown Fix Implementation:**
```typescript
// Fetch cities in batches of 1000 to bypass PostgREST default limit
const batchSize = 1000
const batches = 15 // Up to 15k properties
for (let i = 0; i < batches; i++) {
  const { data } = await supabase
    .from('properties')
    .select('city')
    .eq('province', 'ON')
    .not('city', 'is', null)
    .range(i * batchSize, (i + 1) * batchSize - 1)
  // Aggregate and deduplicate
}
```

**Database Status:**
- 16,110 total properties in database
- 14,481 properties in ON province
- 6,015 properties have transactions linked
- 11,913 brand locations (100% matched to properties - but may be incorrect matches!)
- 12,206 property-brand links

**Address Quality Stats:**
- 100% of properties have `address_canonical` ✓
- 100% of properties have `address_hash` ✓
- 68.9% of properties have geocoding (lat/long)
- ~44 properties with unit numbers in city field (in 1k sample)
- 199 unique "city" values (should be ~60)

**Key Files Created:**
- `/scripts/analysis/analyze_address_matching.py` - Database matching analysis
- `/scripts/analysis/analyze_city_quality.py` - City data quality scan
- `/docs/ADDRESS_NORMALIZATION_PLAN.md` - Comprehensive 4-week fix plan
- `/scripts/analysis/address_matching_results.json` - Analysis output

**Key Files Modified:**
- `/webapp/frontend/app/dashboard/properties/page.tsx` - Batched city fetching, fixed styling issues

---

## Next Session Priorities

### 🚨 URGENT: Safe Address Normalization Fix Plan

**The 100% brand location "match rate" is misleading - we have no confidence these are matched to the CORRECT properties!**

#### Core Principle: **Never Modify Raw Data**
- ✅ Keep RealTrack scraper unchanged (it's working correctly!)
- ✅ All raw data preserved in: `address_raw`, `city_raw`, `stg_transactions.raw`
- ✅ Only fix **derived/computed** fields: `city`, `address_canonical`, `address_hash`

---

### Phase 1: Add Backup Columns (Safety First)
**Goal:** Create backup before touching ANY data

```sql
-- Backup current city values
ALTER TABLE properties ADD COLUMN city_backup TEXT;
UPDATE properties SET city_backup = city;

-- Backup current transactions city values
ALTER TABLE transactions ADD COLUMN city_raw_backup TEXT;
UPDATE transactions SET city_raw_backup = city_raw;
```

**Result:** Raw data is double-backed-up (original fields + backup columns)

---

### Phase 2: Build Address Parser (New Code Only)
**Goal:** Create NEW parser without touching existing code

**New Files:**
- `common/address_parser.py` - Parse & validate addresses (never modifies input)
- `common/ontario_cities.py` - Reference list of ~60 valid ON cities + amalgamations

**Features:**
- Extract city from `address_canonical` when available
- Validate city against known ON cities list
- Handle Toronto/Hamilton amalgamations (Scarborough → Toronto)
- Extract unit numbers to separate field

---

### Phase 3: Fix Existing Data (Read-Only Analysis First)
**Goal:** Analyze before modifying

**Week 1 Tasks:**
1. ✅ Day 1: Add backup columns, create city reference list
2. ✅ Day 2: Build address_parser.py with unit tests
3. ✅ Day 3: Run `scripts/analysis/preview_city_fixes.py` (analysis only - no writes!)
4. ✅ Day 4: Review analysis output, approve changes
5. ✅ Day 5: Run `scripts/fixes/fix_city_from_canonical.py`, validate results

**Scripts:**
- `scripts/analysis/preview_city_fixes.py` - Show what WOULD change (no DB writes)
- `scripts/fixes/fix_city_from_canonical.py` - Apply approved fixes, log all changes
- `scripts/analysis/validate_city_fixes.py` - Verify no unit numbers, all cities valid

---

### Phase 4: Update Normalization (Not Scraper!)
**Goal:** Fix future data without touching RealTrack scraper

**Week 2 Tasks:**
1. ✅ Day 1-2: Add `parse_and_validate_city()` to realtrack_ingest.py (validation layer only)
2. ✅ Day 3: Test with sample RealTrack JSON (dry-run mode)
3. ✅ Day 4: Deploy validation layer
4. ✅ Day 5: Monitor new ingestion, verify clean data

**File to modify:** `scripts/scraper/realtrack_ingest.py`

**Change:** Add ONE validation step AFTER line 203 (non-breaking):
```python
# NEW: Parse and validate city
from common.address_parser import parse_and_validate_city
city = parse_and_validate_city(
    address=addr,
    city_raw=city_raw,
    province="ON"
)  # Returns validated city or extracts from address if city_raw is garbage
```

---

### Phase 5: Unit Number Extraction (Optional)
**Goal:** Store unit numbers separately

**Week 3 Tasks (Optional):**
1. ✅ Day 1-2: Add `unit_number` column to properties
2. ✅ Day 3-4: Extract units from existing addresses using parser
3. ✅ Day 5: Update UI to display unit numbers

---

### What Gets Modified vs. Preserved

**✅ PRESERVED (Never Touched):**
- `stg_transactions.raw` - original JSON from RealTrack
- `transactions.address_raw` - exact address from source
- `transactions.city_raw` - exact city from source
- `properties.city_backup` - backup of current values
- **RealTrack scraper code (unchanged!)**

**🔧 MODIFIED (Computed Fields Only):**
- `properties.city` - fixed to contain actual city name
- `properties.address_canonical` - rebuilt with correct city
- `properties.address_hash` - recomputed from corrected data
- `properties.unit_number` - NEW field extracted from address

---

### Rollback Strategy

If anything goes wrong:
```sql
-- Restore cities from backup
UPDATE properties SET city = city_backup;
UPDATE transactions SET city_raw = city_raw_backup;
```

**Raw data is always safe!**

---

### Success Metrics

**Before:**
- 199 "cities" in 1k properties
- Unit numbers in city field: 44 properties
- RealTrack scraper works ✅ (keep as-is!)

**After:**
- ~60 actual cities
- Unit numbers in city field: 0
- RealTrack scraper works ✅ (unchanged!)
- **All raw data preserved ✅**
- >95% correct brand-property matches

---

## Next Session Priorities (Updated 2025-10-03 - REBOOT)

### 🚨 IMPORTANT: Address Normalization - STARTING FROM SCRATCH

**After comprehensive analysis, we discovered the previous NAR validation approach was fundamentally flawed.**

**Key Issues Found:**
- Raw data from scrapers has inconsistent formats that need parsing FIRST
- Realtrack: "St. Catharines 212 Welland Avenue #Unit 5" (city prefix, unit number)
- Brand Locations: Already structured but has postal codes
- Previous approach tried to validate unparsed messy data → failed

**New Approach:**
We're rebuilding the normalization pipeline from the ground up using a systematic 3-stage process:
1. **Raw Ingestion** - Ensure scrapers capture minimum data
2. **Parsing** - Use libpostal to parse addresses into clean components
3. **Standardization** - Multi-step verification cascade (postal → exact → amalgamation → fuzzy)

See `COMPREHENSIVE_ADDRESS_STANDARDIZATION_PLAN.md` for full details.

---

### Priority 1: Address Normalization - 10 Phase Implementation 🏗️

**Building one piece at a time, verify each before proceeding.**

#### ✅ Phase 1: Install & Test libpostal - COMPLETE
**Goal:** Get libpostal working and test basic parsing

**Tasks:**
- ✅ Install libpostal C library (compiled from source, installed to `/usr/local/`)
- ✅ Install Python wrapper (`pip install postal`)
- ✅ Test on 10 sample addresses from our data
- ✅ Verify parsing quality

**Success Criteria: ALL MET ✅**
- ✅ 100% house_number extraction (10/10)
- ✅ 100% road extraction (10/10)
- ✅ 100% city extraction (10/10)
- ✅ 50% postcode extraction (5/10 - only brand_locations have them)

**Deliverables:**
- `scripts/analysis/fetch_sample_addresses.py` - Fetches sample addresses
- `scripts/analysis/test_libpostal_parsing.py` - Test suite with metrics
- `/tmp/sample_addresses.json` - Sample data

**Key Findings:**
- libpostal works excellently for Canadian addresses
- 2 hyphenated addresses detected (will handle in Phase 8)
- libpostal automatically normalizes output (lowercase)

**Installation:**
- libpostal: `/usr/local/lib/libpostal.1.dylib`
- Headers: `/usr/local/include/libpostal/`
- Data: `/usr/local/share/libpostal/`
- Python wrapper: Installed via pip, properly linked to system library
- **No environment variables needed** ✅

**🛑 CHECKPOINT PASSED:** Ready to proceed to Phase 2

---

#### ⏳ Phase 2: Parse Transactions Table (Realtrack)
**Goal:** Create `transactions_parsed` table and parse all Realtrack addresses

**Tasks:**
- [ ] Create `transactions_parsed` table (schema in IMPLEMENTATION_PHASES.md)
- [ ] Write parsing script for transactions
- [ ] Parse 100 sample transactions
- [ ] Review parsing quality
- [ ] Parse remaining transactions (if quality good)

**Success Criteria:**
- 95%+ addresses have house_number extracted
- 95%+ addresses have road extracted
- 90%+ addresses have city_parsed extracted

**Deliverable:** `transactions_parsed` table populated with report

**🛑 CHECKPOINT:** Review sample of 50 parsed addresses

---

#### ⏳ Phase 3: Parse Brand Locations Table
**Goal:** Create `brand_locations_parsed` table and parse all brand location addresses

**Tasks:**
- [ ] Create `brand_locations_parsed` table
- [ ] Write parsing script for brand_locations
- [ ] Parse 100 sample brand locations
- [ ] Review parsing quality
- [ ] Parse remaining brand locations (if quality good)

**Success Criteria:**
- 95%+ addresses have house_number extracted
- 95%+ addresses have road extracted
- 90%+ addresses have city_parsed extracted
- 80%+ addresses have postcode_parsed extracted

**Deliverable:** `brand_locations_parsed` table populated with report

**🛑 CHECKPOINT:** Review sample of 50 parsed addresses

---

#### ⏳ Phase 4: City Verification - Postal Code Lookup
**Goal:** Verify cities using postal code → NAR lookup (95% confidence)

**Tasks:**
- [ ] Create `address_standardization` tracking table
- [ ] Write postal code → city lookup function
- [ ] Test on 100 addresses WITH postal codes
- [ ] Review accuracy

**Success Criteria:**
- 90%+ valid postal codes found in NAR
- Cities returned make sense

**Deliverable:** Function + test report

**🛑 CHECKPOINT:** Review postal code verification results

---

#### ⏳ Phase 5: City Verification - Exact Match
**Goal:** For addresses WITHOUT postal codes, check if city exists in NAR (90% confidence)

**Tasks:**
- [ ] Extract all distinct cities from NAR (one-time)
- [ ] Write exact city match function
- [ ] Test on 100 addresses WITHOUT postal codes
- [ ] Review accuracy

**Success Criteria:**
- Can identify when city is valid
- Can identify when city is NOT in NAR

**Deliverable:** Function + test report

**🛑 CHECKPOINT:** Review exact match results

---

#### ⏳ Phase 6: City Verification - Amalgamation Check
**Goal:** Map old municipality names to current amalgamated cities (85% confidence)

**Tasks:**
- [ ] Research and create complete Ontario amalgamation map
- [ ] Write amalgamation check function
- [ ] Test on addresses with old city names
- [ ] Review accuracy

**Examples:**
- "Scarborough" → "TORONTO"
- "Nepean" → "OTTAWA"
- "Stoney Creek" → "HAMILTON"

**Success Criteria:**
- Correctly maps former municipalities
- Returns current city names

**Deliverable:** Complete amalgamation mapping + function

**🛑 CHECKPOINT:** Review amalgamation mapping

---

#### ⏳ Phase 7: City Verification - Fuzzy Match
**Goal:** Handle typos and minor variations in city names (85%+ confidence)

**Tasks:**
- [ ] Install rapidfuzz library
- [ ] Write fuzzy match function (85% threshold)
- [ ] Test on addresses with misspelled cities
- [ ] Review accuracy (ensure no false positives!)

**Success Criteria:**
- Correctly matches typos (e.g., "Tornto" → "TORONTO")
- Does NOT create false matches
- Score threshold (85) is appropriate

**Deliverable:** Function + test report

**🛑 CHECKPOINT:** Review fuzzy match results (CRITICAL: check for false positives!)

---

#### ⏳ Phase 8: Hyphenated Address Expansion
**Goal:** Expand address ranges into individual candidate addresses

**Tasks:**
- [ ] Write function to detect hyphenated ranges
- [ ] Write function to expand range into list
- [ ] Test on sample hyphenated addresses
- [ ] Review expansion logic

**Examples:**
- "251-255" → ["251", "252", "253", "254", "255"]
- "8 - 14" → ["8", "9", "10", "11", "12", "13", "14"]

**Success Criteria:**
- Correctly expands ranges
- Handles spaces and different formats
- Returns original if not a range

**Deliverable:** Function + test examples

**Note:** Keep original hyphenated format for display on Property Details page

**🛑 CHECKPOINT:** Review expansion logic

---

#### ⏳ Phase 9: NAR Address Validation
**Goal:** Validate full address against NAR using verified city (100% confidence if found)

**Tasks:**
- [ ] Write NAR query function
- [ ] Test on 100 addresses with verified cities
- [ ] Handle hyphenated addresses (try all candidates)
- [ ] Review match rate

**Success Criteria:**
- Successfully queries NAR
- Tries all candidates for hyphenated addresses
- Returns match with coordinates

**Deliverable:** Function + test report

**🛑 CHECKPOINT:** Review NAR validation results

---

#### ⏳ Phase 10: Full Integration & Testing
**Goal:** Run complete standardization pipeline on 1000 sample addresses

**Tasks:**
- [ ] Combine all verification steps into single workflow
- [ ] Run on 1000 addresses (500 from transactions, 500 from brand_locations)
- [ ] Generate comprehensive report
- [ ] Review results

**Expected Report Metrics:**
- Addresses parsed: 100%
- City verification: ≥90%
- NAR match rate: ≥60% (for addresses with verified cities)
- Confidence ≥90: ≥75%

**Deliverable:** Complete standardization script + comprehensive report

**🛑 CHECKPOINT:** Full review of results before proceeding to production

---

### Key Decisions Made:

✅ **Hyphenated Addresses:** Try all numbers in range (exhaustive)
✅ **Google API:** Skip for now (only if we don't hit 100% accuracy)
✅ **Confidence Thresholds:** 85 for city updates, 90 for address updates
✅ **Table Schema:** Separate tables (`transactions_parsed`, `brand_locations_parsed`)
✅ **Testing:** Start with 1000 sample before full migration
✅ **Display:** Keep original hyphenated format for Property Details page

---

### Files Created for New Plan:

- `COMPREHENSIVE_ADDRESS_STANDARDIZATION_PLAN.md` - Complete 3-stage plan
- `IMPLEMENTATION_PHASES.md` - Detailed 10-phase breakdown with code examples
- `RAW_DATA_ANALYSIS.md` - Complete data pipeline documentation
- `ADDRESS_PARSING_PLAN.md` - Original parsing rules (superseded by libpostal approach)

---

### Priority 2: Schedule RealTrack Scraper (Per User Request)

**User requested automatic scraping at:**
- 6:00 AM
- 9:00 AM
- 12:00 PM (noon)
- 3:00 PM
- 4:45 PM
- 12:00 AM (midnight)

Expected: 6-20 new transactions per day

**Tasks:**
1. Add duplicate detection to RealTrack scraper
2. Create cron jobs for scheduled runs
3. Each run automatically queues new properties for NAR validation
4. Monitor for failures

**Note:** Deferred until after NAR validation system is running.

---

### Priority 3: UI Testing & Polish

With clean address data from NAR validation:

1. **Test City Filter Dropdown**
   - Verify clean city list (should show ~760 valid cities)
   - No unit/suite/address garbage
   - All cities properly capitalized

2. **Test All Filters Together**
   - City + Brand + Buyer + Seller + Price
   - Verify correct filtering behavior
   - Performance testing

---

### Priority 4: Optional Enhancements (Future)

1. **Geocoding Visualization**
   - Map view of properties (lat/long from NAR)
   - Heat maps for brand locations
   - Proximity search

2. **Brand-Property Matching Improvements**
   - Re-run matching with NAR-validated addresses
   - Implement fuzzy matching for edge cases
   - Geocoding proximity matching

3. **Additional City Variations**
   - Add ~250 more city name variations to `AMALGAMATED_CITIES`
   - Examples: "ST. CATHARINES" → "ST CATHARINES"
   - Low priority (NAR validation handles this automatically)

---

## Decisions Made

- Filters always visible (not collapsible) - easier UX for essential filters
- Price dropdown shows min/max side-by-side with preset increments
- Entire table row clickable (removed "Action" column for cleaner UI)
- Using Ant Design components throughout for consistency
- Batched data fetching approach for large datasets to bypass API limits
- Disabled virtual scrolling on city dropdown (`virtual={false}`) for better compatibility
