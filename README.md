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

### Database helpers

```bash
./scripts/run.sh db-setup
./scripts/run.sh db-health                             # test pooler/direct connectivity
./scripts/run.sh db-query "SELECT COUNT(*) FROM transactions;"   # via pooler (fallback to direct)
./scripts/run.sh db-backup
```
### Ingest Realtrack JSON

```bash
./scripts/run.sh scraper realtrack --input path/to/realtrack.json
```

Options:
- `--dry-run` to validate JSON parsing and hashing without DB writes
- `--limit N` to process a subset

Batch ingest all JSON files in a directory:

```bash
./scripts/run.sh scraper realtrack-batch \
  "/absolute/path/to/realtrack/output"    # directory containing *.json
```

The ingestor is idempotent (uses `source_hash`), so re-running is safe.

## Solo Session Flow (One-Person Safety Nets)

This repo uses a lightweight solo flow so I can vibe-code safely:

- Work mostly on `main`.
- Each day at **09:00 Toronto**, CI creates a session branch `ses/YYYY-MM-DD-auto` and a start checkpoint tag.
- Each night at **23:30 Toronto**, CI will:
  - squash-merge that session branch into `main` (if there were commits),
  - create a release tag `rel/YYYY-MM-DD-HHMM-auto`,
  - delete the session branch.
- Every push uploads a ZIP artifact. There’s also a nightly backup ZIP.

Manual scripts (local):
```bash
./scripts/start_session.sh my-desc     # Start a manual session branch
./scripts/checkpoint.sh msg             # Make a checkpoint tag + WIP commit
./scripts/end_session.sh                # Squash-merge back to main + release tag
```

Note: GitHub’s cron runs in UTC. We schedule both EDT and EST times to cover DST automatically.

Suggested git aliases for faster solo flow:
```ini
[alias]
  st = status -sb
  lg = log --oneline --graph --decorate --all
  wip = !f(){ d=$(date +%F-%H%M); git add -A && git commit -m "wip: $d"; }; f
```
