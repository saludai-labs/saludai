#!/usr/bin/env bash
# Sync clean version to public remote (saludai-labs/saludai)
# Uses a persistent local branch (public-main) to preserve incremental history.
# Usage: bash sync-public.sh "commit message"
set -euo pipefail

MSG="${1:-sync: $(date +%Y-%m-%d)}"
IGNORE_FILE=".public-ignore"
PUBLIC_BRANCH="public-main"
REMOTE="public"

if [ ! -f "$IGNORE_FILE" ]; then
  echo "ERROR: $IGNORE_FILE not found"
  exit 1
fi

# Load exclude patterns
EXCLUDES=()
while IFS= read -r pattern; do
  pattern="$(echo "$pattern" | tr -d '\r')"
  [ -z "$pattern" ] && continue
  [[ "$pattern" == \#* ]] && continue
  EXCLUDES+=("$pattern")
done < "$IGNORE_FILE"

# Save current branch
CURRENT_BRANCH="$(git branch --show-current)"

# Switch to persistent public branch
if git show-ref --verify --quiet "refs/heads/$PUBLIC_BRANCH"; then
  git checkout "$PUBLIC_BRANCH"
else
  echo "ERROR: $PUBLIC_BRANCH branch not found. It should already exist from initial setup."
  exit 1
fi

# Sync all files from dev main
git checkout "$CURRENT_BRANCH" -- .

# Remove excluded files from staging and working tree
for pat in "${EXCLUDES[@]}"; do
  git rm -rf --cached "$pat" 2>/dev/null || true
  rm -rf "$pat" 2>/dev/null || true
done

# Check if there are changes
if git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  echo "No changes to sync."
  git checkout -f "$CURRENT_BRANCH"
  exit 0
fi

# Stage everything and commit
git add -A
git commit -m "$MSG"

# Push incrementally (no force)
git push "$REMOTE" "$PUBLIC_BRANCH:main"

# Return to dev branch
git checkout -f "$CURRENT_BRANCH"

echo "Done. Public repo updated."
