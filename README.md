## Cleo — Unify Data. Unlock Deals.

This repo contains the code and assets for the Cleo commercial real estate data platform.

Start with `Cleo App Development Plan.md` for the high-level roadmap. This README provides quickstart commands.

### Quickstart

1) Copy environment example:

```bash
cp .env.example .env
```

2) Check local prerequisites:

```bash
./scripts/setup/check_prerequisites.sh
```

3) Create Python venv and install deps:

```bash
./scripts/run.sh setup
```

4) Apply base Supabase schema (requires a Postgres connection string in `DATABASE_URL`):

```bash
./scripts/run.sh db-setup
```

For a detailed plan, see `Cleo App Development Plan.md`.
### Ingest Realtrack JSON

```bash
./scripts/run.sh scraper realtrack --input path/to/realtrack.json
```

Options:
- `--dry-run` to validate JSON parsing and hashing without DB writes
- `--limit N` to process a subset

