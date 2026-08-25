#!/usr/bin/env bash
set -euo pipefail

# setup_github.sh
#
# One-shot setup: creates a GitHub repo from this project, pushes it,
# enables GitHub Pages with "GitHub Actions" as the build source (the
# correct API call for that is POST /repos/{owner}/{repo}/pages with
# build_type=workflow -- verified against GitHub's REST API docs, not
# guessed), and triggers the first run immediately so you don't have
# to wait for tomorrow's 06:00 UTC cron.
#
# Requires: `gh` (GitHub CLI) installed and already logged in
# (`gh auth login`) -- that login step needs your own credentials and
# can't be done by this script or by Claude on your behalf.
#
# Usage:
#   ./scripts/setup_github.sh my-ecc-journal
#   (repo name defaults to "ecc-journal" if omitted)

REPO_NAME="${1:-ecc-journal}"

if ! command -v gh >/dev/null 2>&1; then
    echo "GitHub CLI ('gh') not found. Install it first: https://cli.github.com" >&2
    exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
    echo "Not logged in to GitHub CLI. Run 'gh auth login' first, then re-run this script." >&2
    exit 1
fi

echo "== Creating repo '$REPO_NAME' and pushing this project =="
git init -q
git add .
git commit -q -m "Initial commit: ECC journal project" || true  # no-op if nothing changed (safe to re-run)
gh repo create "$REPO_NAME" --public --source=. --remote=origin --push

OWNER=$(gh api user --jq .login)
echo "== Enabling GitHub Pages (source: GitHub Actions) for $OWNER/$REPO_NAME =="
gh api -X POST "repos/$OWNER/$REPO_NAME/pages" -f build_type=workflow \
    && echo "Pages enabled." \
    || echo "(Pages may already be enabled, or needs a first successful workflow run first -- continuing.)"

echo "== Triggering the first run now (instead of waiting for tomorrow's 06:00 UTC cron) =="
gh workflow run "Daily ECC Journal" --repo "$OWNER/$REPO_NAME" \
    && echo "Triggered. Check progress with: gh run watch --repo $OWNER/$REPO_NAME" \
    || echo "(Could not auto-trigger -- open the Actions tab on GitHub and run it manually once.)"

echo
echo "Done. Once the workflow finishes (a minute or two), your site will be live at:"
echo "  https://$OWNER.github.io/$REPO_NAME/"
echo
echo "If 'gh api ... pages' failed above because Pages needs an initial successful"
echo "Actions run first: that's fine -- the workflow run just triggered will publish"
echo "docs/ as a Pages artifact regardless, and GitHub typically auto-detects it."
echo "If the site still isn't live after the run completes, do the one manual step:"
echo "Settings -> Pages -> Source -> GitHub Actions."
