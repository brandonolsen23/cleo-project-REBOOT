#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)

if [ $# -lt 1 ]; then
  echo "Usage: $0 <directory-of-json-files> [--max-files N] [--offset N] [--dry-run]" >&2
  exit 1
fi

DIR=$1
shift || true

if [ ! -d "$DIR" ]; then
  echo "Not a directory: $DIR" >&2
  exit 1
fi

MAX_FILES=0
OFFSET=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-files)
      MAX_FILES=${2:-0}
      shift 2 || true
      ;;
    --offset)
      OFFSET=${2:-0}
      shift 2 || true
      ;;
    *)
      break
      ;;
  esac
done

# Build a newline-delimited file list (portable)
LIST_FILE="$ROOT_DIR/logs/realtrack_files.txt"
mkdir -p "$ROOT_DIR/logs"
find "$DIR" -type f -name '*.json' | sort > "$LIST_FILE"

total=$(wc -l < "$LIST_FILE" | tr -d ' ')
start=$(( OFFSET + 1 ))
end=$total
if (( MAX_FILES > 0 )); then
  end=$(( OFFSET + MAX_FILES ))
  if (( end > total )); then end=$total; fi
fi

echo "Found $total files. Processing lines $start to $end."

count=0
sed -n "${start},${end}p" "$LIST_FILE" | while IFS= read -r f; do
  echo "Ingesting: $f"$'\n'
  PYTHONPATH="$ROOT_DIR" "$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/scripts/scraper/realtrack_ingest.py" --input "$f" "$@"
  count=$((count+1))
done

echo "Completed. Files processed: $count (from $total total)"
