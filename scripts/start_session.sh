#!/usr/bin/env bash
set -euo pipefail

DESC="${1:-vibe}"
DATE="$(date +%F)"
TIME="$(date +%H%M)"
BRANCH="ses/${DATE}-${DESC}"

REPO_TOP=$(git rev-parse --show-toplevel)
cd "$REPO_TOP"

# Save any local mess
git stash push -u -m "pre-session-${DATE}-${TIME}" || true

# Sync main
git fetch origin
git checkout main
git pull --ff-only origin main

# Create or reuse session branch
if git rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
  git checkout "$BRANCH"
else
  git checkout -b "$BRANCH"
  git commit --allow-empty -m "chore(session): start ${BRANCH}"
  git push -u origin "$BRANCH"
fi

# First checkpoint tag
TAG="cp/${DATE}-${TIME}-start"
git tag -a "$TAG" -m "session start ${BRANCH}" || true
git push origin "$TAG" || true

echo "✅ Session started on branch: $BRANCH"
echo "   Checkpoint tag: $TAG"
