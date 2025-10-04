# CLAUDE.md - Project Context for AI Assistance

**Last Updated:** 2025-10-03
**Project:** Cleo - Real Estate Data Platform
**Version:** 2.0 (REBOOT)

---

## Project Overview

**What is Cleo?**
Platform for tracking commercial real estate transactions and brand locations across Ontario. Ingests transaction data from RealTrack, matches properties to brand locations, and provides analytics/filtering UI.

**Core Value Proposition:**
- Track which brands (Tim Hortons, McDonald's, etc.) are buying/selling properties
- Analyze commercial real estate trends by city, brand, price
- High-quality address matching using NAR 2024 database (5.7M Ontario addresses)

---

## Architecture

### Tech Stack
- **Frontend:** Next.js 14, TypeScript, Ant Design, TailwindCSS
- **Backend:** Python 3.x (scrapers, services, analysis)
- **Database:** PostgreSQL (Supabase hosted)
- **APIs:** RealTrack (transactions), NAR 2024 (address validation)

### Key Data Sources
1. **RealTrack** - Transaction data (sales, buyers, sellers, addresses)
2. **Brand Locations** - Scraped from brand websites/Google Places
3. **NAR 2024** - Statistics Canada National Address Register (5.7M Ontario addresses, 1,153 cities)

### Database Schema (Core Tables)

```
properties
├── id (uuid, primary key)
├── address_canonical (text) - normalized full address
├── address_hash (text) - for matching/deduplication
├── city (text) - normalized city name (TO FIX - see Critical Issues)
├── province (text)
├── postal_code (text)
├── latitude, longitude (decimal) - from NAR validation
├── city_backup (text) - safety backup before fixes
└── Raw data preserved in stg_transactions.raw (jsonb)

transactions
├── id (uuid)
├── property_id (uuid) → properties
├── transaction_date (date)
├── price (numeric)
├── buyer_name, seller_name (text)
├── address_raw, city_raw (text) - NEVER MODIFIED
└── Raw JSON preserved in stg_transactions.raw

brand_locations
├── id (uuid)
├── brand (text) - e.g., "Tim Hortons", "McDonald's"
├── address (text)
├── city (text)
├── postal_code (text)
└── status (text)

nar_validation_queue, nar_validation_results, nar_validation_history
└── See NAR Validation System section

brand_location_property_links
├── brand_location_id (uuid) → brand_locations
├── property_id (uuid) → properties
└── Matching based on address_hash (UNRELIABLE until addresses fixed)
```

---

## Critical Principles

### 🚨 NEVER MODIFY RAW DATA
- `stg_transactions.raw` - original JSON from RealTrack (SACRED)
- `transactions.address_raw`, `transactions.city_raw` - exact from source
- **Only modify computed/derived fields:** `city`, `address_canonical`, `address_hash`
- Always create backup columns before fixing data

### 🚨 Address Data Quality is BROKEN (Active Fix In Progress)
- City field contains garbage: unit numbers, full addresses, sub-municipalities
- 199 unique "city" values in 1k properties (should be ~60)
- Example: `city = "Unit 1"` instead of `city = "BRAMPTON"`
- **Impact:** Brand-property matching may be matching WRONG properties
- **Fix:** 10-phase address normalization plan (see Current Work)

### Keep Scrapers Simple
- RealTrack scraper works correctly - captures raw data as-is
- Validation/normalization happens AFTER ingestion, not during
- Scrapers should never validate or clean data

---

## Directory Structure

```
cleo-project-REBOOT/
├── webapp/frontend/          # Next.js app
│   ├── app/
│   │   ├── dashboard/
│   │   │   ├── properties/   # Properties table with filters
│   │   │   ├── brands/
│   │   │   └── analytics/
│   │   └── api/              # Next.js API routes
│   └── components/
│
├── scripts/
│   ├── scraper/
│   │   ├── realtrack_ingest.py           # Main transaction scraper
│   │   └── post_realtrack_queue_validation.py  # Queues for NAR validation
│   ├── services/
│   │   └── nar_validation_service.py     # Background NAR validation service
│   ├── setup/
│   │   └── setup_nar_validation.py       # Database setup for NAR system
│   ├── backfill/
│   │   └── backfill_nar_validation.py    # Backfill 16k existing properties
│   ├── monitoring/
│   │   └── nar_validation_status.py      # Monitor validation progress
│   └── analysis/
│       └── [various analysis scripts]
│
├── common/
│   ├── nar_validator.py        # NAR validation with caching
│   ├── queue_nar_validation.py # Queue helper
│   └── [future: address_parser.py, ontario_cities.py]
│
├── docs/
│   ├── NAR_VALIDATION_SYSTEM.md
│   └── ADDRESS_FIX_SUMMARY.md
│
├── NEXT.md                     # Session notes, next priorities (UPDATE REGULARLY)
├── CLAUDE.md                   # This file (UPDATE ON MAJOR CHANGES)
└── COMPREHENSIVE_ADDRESS_STANDARDIZATION_PLAN.md
```

---

## Current Work (Active)

### 🏗️ Address Normalization - 10 Phase Plan
**Status:** Phase 0 - Planning complete, ready to start Phase 1
**Goal:** Fix city field garbage using libpostal parsing + NAR validation
**See:** `COMPREHENSIVE_ADDRESS_STANDARDIZATION_PLAN.md`, `IMPLEMENTATION_PHASES.md`

**Phases:**
1. Install & test libpostal
2. Parse transactions table (create `transactions_parsed`)
3. Parse brand_locations table (create `brand_locations_parsed`)
4. City verification - postal code lookup
5. City verification - exact match
6. City verification - amalgamation (Scarborough → Toronto)
7. City verification - fuzzy match
8. Hyphenated address expansion (251-255 → [251, 252, 253, 254, 255])
9. NAR address validation
10. Full integration & testing (1000 sample addresses)

**Each phase has checkpoint before proceeding.**

### ✅ NAR Validation System - COMPLETE (2025-10-03)
- Background service validates addresses against NAR 2024 database
- Batch processing: 100 properties in 10-30 seconds
- Cache hit rate: 60-80% (200x faster)
- Queued from RealTrack scraper automatically
- Ready for deployment (backfill 16k properties in 4-8 hours)

---

## System Configuration

### Sudo Access for AI Assistant
**Configured:** 2025-10-03

The sudoers file is configured to allow `make` and `brew` commands without password:
```
%admin ALL=(ALL) NOPASSWD: /usr/bin/make, /usr/local/bin/brew, /opt/homebrew/bin/brew
```

This allows the AI assistant to run these commands when needed without manual intervention.

**Files modified:**
- `/etc/sudoers` (via `sudo visudo`)

**Security note:** Limited to specific safe commands only.

---

## Common Commands

### Frontend Development
```bash
cd webapp/frontend
npm install
npm run dev              # Start dev server on localhost:3000
npm run build            # Production build
npx next lint            # Lint check
```

### Database Access
```bash
# Set environment variable (already in your shell config)
export DATABASE_URL='postgresql://postgres:Osc1Rot%40t3ion974was627@db.igteejiyhogrxhncigrl.supabase.co:5432/postgres'

# Direct psql access
psql $DATABASE_URL

# Quick queries
psql $DATABASE_URL -c "SELECT COUNT(*) FROM properties;"
```

### NAR Validation System
```bash
# Status check
python3 scripts/monitoring/nar_validation_status.py

# Start service
python3 scripts/services/nar_validation_service.py

# Backfill existing properties
python3 scripts/backfill/backfill_nar_validation.py
```

### Address Parsing (libpostal)
```bash
# Test libpostal parsing
python3 scripts/analysis/test_libpostal_parsing.py

# Fetch sample addresses
python3 scripts/analysis/fetch_sample_addresses.py
```

**Installation:**
- libpostal C library: `/usr/local/lib/libpostal.1.dylib`
- Python wrapper: `pip install postal` (installed in venv)
- No environment variables needed (properly linked)

### Scraper
```bash
# Manual RealTrack scrape
python3 scripts/scraper/realtrack_ingest.py
```

---

## External Resources

### NAR 2024 Database
- **Access:** Via `DATABASE_URL` (nar_addresses, nar_cities tables)
- **Size:** 5.7M Ontario addresses, 1,153 cities
- **Schema:**
  ```
  nar_addresses: street_number, street_name, city, province, postal_code, latitude, longitude
  nar_cities: city_name, province
  ```

### APIs
- **RealTrack:** Proprietary transaction data (credentials in env vars)
- **Supabase:** PostgreSQL database (PostgREST API available)

---

## Known Issues & Gotchas

### Supabase PostgREST Limit
- **Issue:** Default 1000 row limit on queries
- **Solution:** Use `.range(from, to)` in batched loops
- **Example:** Fetching cities for dropdown (see `webapp/frontend/app/dashboard/properties/page.tsx:280-295`)

### Address Matching Unreliable
- **Issue:** 100% brand location "match rate" is MISLEADING
- **Reason:** Garbage in city field means address_hash is wrong
- **Status:** Fix in progress (10-phase plan)
- **Don't trust:** `brand_location_property_links` until addresses fixed

### Toronto Amalgamation
- Must map: Scarborough, Etobicoke, North York, East York → TORONTO
- Same for Hamilton (Ancaster, Dundas, Stoney Creek, etc.)
- NAR database uses current amalgamated names

---

## What NOT to Do

❌ **Don't modify RealTrack scraper logic** (it works - captures raw data correctly)
❌ **Don't touch raw data columns** (`stg_transactions.raw`, `address_raw`, `city_raw`)
❌ **Don't trust brand-property matches yet** (addresses need fixing first)
❌ **Don't create new .md files** unless explicitly requested
❌ **Don't assume city field is clean** (it's full of garbage)
❌ **Don't run fixes without backup columns first**

---

## Maintenance Guidelines

### When to Update CLAUDE.md
1. **Major architectural changes** (new tables, services, APIs)
2. **New critical principles discovered** (like "never modify raw data")
3. **Completion of major phases** (mark ✅, update status)
4. **New gotchas/known issues found**
5. **Change in tech stack or dependencies**

### When to Update NEXT.md
1. **Daily/session work** (what was completed today)
2. **Next immediate priorities** (what to work on next session)
3. **Short-term task tracking** (current phase checklist)

### Division of Responsibility
- **CLAUDE.md** = Long-term project context (architecture, principles, gotchas)
- **NEXT.md** = Short-term session notes (what's done, what's next)
- **Plan docs** (e.g., IMPLEMENTATION_PHASES.md) = Detailed specifications

### Git Tracking
- **Do commit:** CLAUDE.md on major changes
- **Do commit:** NEXT.md after each session
- **Message format:** "Update CLAUDE.md - add NAR validation system" or "Update NEXT.md - Phase 1 complete"

---

## Quick Start for New AI Session

1. **Read this file first** (you're doing it!)
2. **Read NEXT.md** for current priorities and recent work
3. **Ask user what to work on** (don't assume based on files alone)
4. **Check current git status** to see uncommitted changes
5. **Create todo list** for multi-step tasks
6. **Update NEXT.md** at end of session with progress

---

## Success Metrics (Goals)

### Current State
- 16,110 properties in database
- 14,481 Ontario properties
- 11,913 brand locations
- 12,206 brand-property links (UNRELIABLE - addresses broken)
- 199 unique "city" values in 1k sample (should be ~60)

### Target State (After Address Fix)
- ~60 valid Ontario cities
- 0 unit numbers in city field
- >95% correct brand-property matches
- NAR validation: ≥90% city verification, ≥60% full address match
- Confidence ≥90 for city updates, ≥100 for address updates

---

## Contact & References

- **User:** Brandon Olsen
- **Project Start:** 2025-10-02 (REBOOT)
- **Database:** Supabase (credentials in env vars)
- **Key Docs:** NAR_VALIDATION_SYSTEM.md, COMPREHENSIVE_ADDRESS_STANDARDIZATION_PLAN.md
