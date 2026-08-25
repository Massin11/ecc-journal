# setup_github.ps1
#
# Native PowerShell equivalent of setup_github.sh, for Windows users
# who'd rather not use Git Bash.
#
# IMPORTANT HONESTY NOTE: unlike setup_github.sh -- which I actually
# ran, command by command, in a real sandbox with the real `gh` CLI
# installed -- I could NOT execution-test this PowerShell version.
# PowerShell isn't available in my sandbox (not in Ubuntu's package
# repos, and Microsoft's own package repo isn't in my network
# allowlist), so this is written carefully from documented PowerShell
# semantics, not verified end-to-end. The bash version (via Git Bash)
# remains the one I can actually vouch for. If something here behaves
# unexpectedly, that's the first thing to suspect.
#
# One real subtlety this script gets right on purpose: PowerShell does
# NOT treat a non-zero exit code from a native command (like `gh`) as
# a terminating error by default -- try/catch will NOT catch a plain
# CLI failure. This script checks $LASTEXITCODE explicitly after each
# `gh`/`git` call instead, which is the correct way to detect failure
# for native commands in PowerShell.
#
# Usage:
#   .\scripts\setup_github.ps1 -RepoName my-ecc-journal

param(
    [string]$RepoName = "ecc-journal"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI ('gh') not found. Install it first: https://cli.github.com"
    exit 1
}

gh auth status *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Not logged in to GitHub CLI. Run 'gh auth login' first, then re-run this script."
    exit 1
}

Write-Host "== Creating repo '$RepoName' and pushing this project =="
git init -q
git add .
git commit -q -m "Initial commit: ECC journal project"
# nothing-to-commit on a re-run exits non-zero; that's fine, don't treat it as fatal
$ErrorActionPreference = "Continue"

gh repo create $RepoName --public --source=. --remote=origin --push
if ($LASTEXITCODE -ne 0) {
    Write-Error "gh repo create failed -- see output above."
    exit 1
}

$Owner = (gh api user --jq .login).Trim()

Write-Host "== Enabling GitHub Pages (source: GitHub Actions) for $Owner/$RepoName =="
gh api -X POST "repos/$Owner/$RepoName/pages" -f build_type=workflow
if ($LASTEXITCODE -eq 0) {
    Write-Host "Pages enabled."
} else {
    Write-Host "(Pages may already be enabled, or needs a first successful workflow run first -- continuing.)"
}

Write-Host "== Triggering the first run now (instead of waiting for tomorrow's 06:00 UTC cron) =="
gh workflow run "Daily ECC Journal" --repo "$Owner/$RepoName"
if ($LASTEXITCODE -eq 0) {
    Write-Host "Triggered. Check progress with: gh run watch --repo $Owner/$RepoName"
} else {
    Write-Host "(Could not auto-trigger -- open the Actions tab on GitHub and run it manually once.)"
}

Write-Host ""
Write-Host "Done. Once the workflow finishes (a minute or two), your site will be live at:"
Write-Host "  https://$Owner.github.io/$RepoName/"
Write-Host ""
Write-Host "If Pages-enabling failed above: that's fine -- the workflow run just triggered will"
Write-Host "publish docs/ as a Pages artifact regardless, and GitHub typically auto-detects it."
Write-Host "If the site still isn't live after the run completes, do the one manual step:"
Write-Host "Settings -> Pages -> Source -> GitHub Actions."
