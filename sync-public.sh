#!/usr/bin/env bash
# Sync clean version to public remote (saludai-labs/saludai)
# Usage: bash sync-public.sh "commit message"
set -euo pipefail

MSG="${1:-sync: $(date +%Y-%m-%d)}"
IGNORE_FILE=".public-ignore"

if [ ! -f "$IGNORE_FILE" ]; then
  echo "ERROR: $IGNORE_FILE not found"
  exit 1
fi

echo "Creating clean orphan branch..."
git checkout --orphan public-sync

echo "Unstaging excluded files..."
while IFS= read -r pattern; do
  pattern="$(echo "$pattern" | tr -d '\r')"
  [ -z "$pattern" ] && continue
  [[ "$pattern" == \#* ]] && continue
  git reset HEAD -- "$pattern" 2>/dev/null || true
done < "$IGNORE_FILE"

echo "Committing..."
git commit -m "$MSG"

echo "Pushing to public remote..."
git push public public-sync:main --force

echo "Returning to main..."
git checkout -f main
git branch -D public-sync

echo "Done. Public repo updated."
