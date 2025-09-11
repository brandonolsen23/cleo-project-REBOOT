#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
export ROOT_DIR

# Load env if present
if [ -f "$ROOT_DIR/.env" ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' "$ROOT_DIR/.env" | xargs -I{} echo {})
fi

DATABASE_URL=${DATABASE_URL:-}

if [ -z "$DATABASE_URL" ]; then
  echo "DATABASE_URL not set. Add it to .env or export it in your shell." >&2
  exit 1
fi

sql() {
  local file=$1
  echo "Applying: $file"
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$file"
}

backup() {
  mkdir -p "$ROOT_DIR/backups"
  local ts
  ts=$(date +%Y%m%d_%H%M%S)
  local out="$ROOT_DIR/backups/cleo_${ts}.sql"
  echo "Creating backup: $out"
  pg_dump --no-owner --no-privileges "$DATABASE_URL" > "$out"
  echo "Backup complete."
}

usage() {
  cat <<EOF
Usage: $0 <init|migrate|backup|restore FILE>

Commands:
  init           Apply base schema at config/supabase/setup_supabase.sql
  migrate        Apply migrations in config/supabase/migrations (if any)
  backup         Dump database to ./backups
  restore FILE   Restore from a backup file
EOF
}

cmd=${1:-}
case "$cmd" in
  init)
    sql "$ROOT_DIR/config/supabase/setup_supabase.sql"
    ;;
  migrate)
    if [ -d "$ROOT_DIR/config/supabase/migrations" ]; then
      shopt -s nullglob
      for f in "$ROOT_DIR/config/supabase/migrations"/*.sql; do
        sql "$f"
      done
      shopt -u nullglob
    else
      echo "No migrations directory found."
    fi
    ;;
  backup)
    backup
    ;;
  restore)
    file=${2:-}
    if [ -z "$file" ] || [ ! -f "$file" ]; then
      echo "Provide a valid backup file to restore." >&2
      exit 1
    fi
    echo "Restoring from $file"
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$file"
    ;;
  *)
    usage
    exit 1
    ;;
esac
