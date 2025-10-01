#!/usr/bin/env bash
set -euo pipefail

BRANCH=$(git rev-parse --abbrev-ref HEAD)
DATE="$(date +%F)"
TIME="$(date +%H%M)"

if [[ "$BRANCH" != ses/* ]]; then
  echo "This doesn't look like a session branch: $BRANCH"
  exit 0
fi

./scripts/checkpoint.sh end || true

git fetch origin
git checkout main
git pull --ff-only origin main

# Squash merge session branch (tolerate no changes)
if git merge --squash "$BRANCH"; then
  git commit -m "feat: merge ${BRANCH} (squash)"
else
  echo "ℹ️ Nothing to squash from ${BRANCH}."
fi

git push origin main

REL="rel/${DATE}-${TIME}"
git tag -a "$REL" -m "release after ${BRANCH}" || true
git push origin "$REL" || true

# Clean up remote/local branch
git branch -D "$BRANCH" || true
git push origin --delete "$BRANCH" || true

echo "✅ Session ended. Release tag: $REL"
