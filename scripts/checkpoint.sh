#!/usr/bin/env bash
set -euo pipefail

DESC="${1:-wip}"
DATE="$(date +%F)"
TIME="$(date +%H%M)"
TAG="cp/${DATE}-${TIME}-${DESC}"

# Commit WIP if needed
if ! git diff --quiet || ! git diff --cached --quiet; then
  git add -A
  git commit -m "chore(cp): ${TAG}"
fi

git tag -a "$TAG" -m "checkpoint ${TAG}" || true
git push origin HEAD --tags

echo "🔖 Checkpoint: $TAG"
