#!/usr/bin/env bash
set -euo pipefail

missing=()

check() {
  if ! command -v "$1" >/dev/null 2>&1; then
    missing+=("$1")
  else
    printf "%-12s %s\n" "$1" "$($1 --version 2>/dev/null | head -n1 || echo 'found')"
  fi
}

echo "Checking prerequisites..."
check python3
check node
check docker
check psql

if [ ${#missing[@]} -gt 0 ]; then
  echo "\nMissing required tools: ${missing[*]}" >&2
  echo "Please install them and re-run."
  exit 1
fi

echo "\nAll prerequisites found."

