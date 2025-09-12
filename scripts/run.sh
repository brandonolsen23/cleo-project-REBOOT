#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export ROOT_DIR

# Load environment variables from .env if present
if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "$ROOT_DIR/.env"
  set +a
fi

usage() {
  cat <<EOF
Usage: $0 <command> [args]

Commands:
  setup                 Run environment setup checks
  db-setup              Apply base Supabase schema
  db-migrate            Run pending migrations (if any)
  db-backup             Create a DB backup into ./backups
  scraper <name>        Run a scraper (placeholder)
  frontend-dev          Start frontend dev server (placeholder)
  help                  Show this help
EOF
}

cmd=${1:-help}
case "$cmd" in
  setup)
    "$ROOT_DIR/scripts/setup/check_prerequisites.sh"
    "$ROOT_DIR/scripts/setup/setup_python.sh"
    ;;
  db-setup)
    "$ROOT_DIR/scripts/db/manage_db.sh" init
    ;;
  db-migrate)
    "$ROOT_DIR/scripts/db/manage_db.sh" migrate
    ;;
  db-backup)
    "$ROOT_DIR/scripts/db/manage_db.sh" backup
    ;;
  standardize-properties)
    shift || true
    PYTHONPATH="$ROOT_DIR" "$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/scripts/db/standardize_properties.py" "$@"
    ;;
  scraper)
    shift || true
    subcmd=${1:-}
    case "$subcmd" in
      realtrack)
        shift || true
        PYTHONPATH="$ROOT_DIR" "$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/scripts/scraper/realtrack_ingest.py" "$@"
        ;;
      realtrack-batch)
        shift || true
        "$ROOT_DIR/scripts/scraper/ingest_dir.sh" "$@"
        ;;
      *)
        echo "Unknown scraper: $subcmd" >&2
        exit 1
        ;;
    esac
    ;;
  frontend-dev)
    echo "[placeholder] Start Next.js dev server: (to be implemented)"
    ;;
  help|--help|-h)
    usage
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    usage
    exit 1
    ;;
esac
