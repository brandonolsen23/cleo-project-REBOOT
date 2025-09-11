# Cleo – Unify Data. Unlock Deals.

**C**ombine (consolidate listings & transactions)  
**L**ocate (geo-tag, address standardization)  
**E**valuate (data analytics & insights)  
**O**ptimize (drive deals & maximize ROI)

---

## Project Overview

Cleo is a real estate data platform that consolidates and standardizes data from multiple sources (e.g., RealTrack transactions, retail brand directories) into a unified Supabase database, surfaced through a web application with mapping, filtering, and enrichment features.

The ultimate goal is to create a living “master list” of Canadian retail/industrial properties, enriched with transaction history, ownership contacts, and brand presence.

---

## Core Roadmap

### Phase 1 – Data Ingestion
- [ ] Supabase setup
  - Create project and apply base schema (see `/config/supabase/setup_supabase.sql`)
  - Tables: properties, transactions, owners, brands, brand_locations, notes, etc.
- [ ] Ingest Realtrack JSON
  - Parse existing JSON files into `stg_transactions`
  - Compute `source_hash` for idempotency
  - Move normalized data into `transactions` + link to `properties`

### Phase 2 – Address Standardization
- [ ] Integrate libpostal parsing + Geocod.io API (later add Canada Post AddressComplete for gold-standard verification)
- [ ] Generate canonical address strings and `address_hash`
- [ ] Store lat/lng, accuracy, and geocode source
- [ ] Deduplicate properties by address_hash or spatial match

### Phase 3 – Brand Locations
- [ ] Scrape ~160 retail brand directories (monthly)
- [ ] Standardize brand addresses (same pipeline as Phase 2)
- [ ] Match brand locations to properties (`property_brand_links`) via:
  - Exact `address_hash`
  - Geo + postal code proximity (≤20m)

### Phase 4 – Transactions & Enrichment
- [ ] Link transactions to properties
- [ ] Build owners + contacts tables
- [ ] Integrate enrichment (Apollo/ZoomInfo, future: GeoWarehouse/zoning)
- [ ] Add notes system for deal tracking

### Phase 5 – Web Application
- [ ] Frontend (React/Next.js)
  - Mapbox/Leaflet cluster map
  - Filter panel: brand, city, transaction date
  - Property detail drawer (transactions, brands, notes)
- [ ] Backend/API
  - Supabase APIs or Next.js API routes
  - Endpoints: `/properties`, `/property/:id`, `/brands`, `/search`, `/notes`

### Phase 6 – Automation & Scheduling
- [ ] Scrapers containerized (Docker)
- [ ] Deploy to Google Cloud Run
- [ ] Schedule daily jobs with Cloud Scheduler
- [ ] Logging + monitoring: Supabase logs, Sentry, Slack alerts
- [ ] Materialized views for quick UI queries (e.g., `latest_tx_per_property`)

---

## Technical Architecture

- Database: Supabase (PostgreSQL)  
- Scrapers: Python (Playwright, BeautifulSoup, lxml), Dockerized  
- Address Standardization: libpostal + Geocod.io API (later AddressComplete)  
- Frontend: React / Next.js (Vercel-hosted)  
- Mapping: Mapbox GL JS (preferred) or Leaflet  
- Deployment: Cloud Run (scrapers/API), Vercel (frontend)  
- CI/CD: GitHub Actions for linting, testing, Docker builds, deploys  
- Automation: Cloud Scheduler + Cloud Run Jobs  
- Version Control: GitHub  

---

## Project Structure

```
cleo/
├── assets/                     # Static assets
│   ├── data/                   # Static data files
│   └── images/                 # Images
│
├── backups/                    # DB backups
├── common/                     # Shared modules (db, geocoding, logging, utils)
├── config/                     # Config files
│   ├── docker/                 # Docker configs
│   ├── supabase/               # Supabase setup & migrations
│   └── scrapers/               # Scraper configs
├── docs/                       # Documentation (architecture, setup, api, db)
├── logs/                       # Log files (scraper runs, etc.)
├── scripts/                    # Scripts for tasks
│   ├── setup/                  # Environment & setup scripts
│   ├── deployment/             # Deployment scripts
│   ├── scraper/                # Scraper runner scripts
│   ├── db/                     # DB management scripts
│   └── run.sh                  # Central runner script
├── scrapers/                   # Scraper modules (one per brand/source)
├── tests/                      # Tests
├── webapp/                     # Web application
│   ├── frontend/               # Next.js frontend
│   └── api/                    # API (if not using Supabase edge functions)
└── README.md                   # This file
```

---

## Development Workflow

### Prerequisites
- Python 3.10+  
- Node.js 18+  
- Docker + Docker Compose  
- Git + PostgreSQL client tools  

Check prerequisites:
```bash
./scripts/setup/check_prerequisites.sh
```

### Setup
```bash
./scripts/run.sh setup
```
- Creates Python venv  
- Installs requirements  
- Sets up `.env` from `.env.example`  
- Applies base schema  

### Database
```bash
./scripts/run.sh db-setup
./scripts/db/manage_db.sh migrate
./scripts/db/manage_db.sh backup
```

### Running Scrapers
```bash
./scripts/run.sh scraper realtrack
./scripts/scraper/run_scraper.sh shoppers --options
```

### Frontend
```bash
./scripts/run.sh frontend-dev
```

### Deployment
```bash
./scripts/deployment/deploy.sh staging all
./scripts/deployment/deploy.sh production frontend
```

---

## Future Enhancements

- Zoning / GeoWarehouse data enrichment  
- AI buyer/seller pattern detection  
- Advanced dashboards & analytics  
- Role-based access & sharing inside Supabase  

---

## Next Up

👉 Phase 1, Step 1: Supabase setup + schema creation  
This is the first execution step. Once done, mark it complete here and move to JSON ingestion.
