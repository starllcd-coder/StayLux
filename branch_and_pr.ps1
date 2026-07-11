# Branch, commit and push helper for StayLux
Write-Host "Branch + PR helper"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "git not found in PATH. Please install git or run the manual commands in COMMIT_INSTRUCTIONS.md" -ForegroundColor Yellow
    exit 1
}

$time = Get-Date -Format "yyyyMMddHHmmss"
$branch = "mobile/customer-only-idempotency-$time"

Write-Host "Creating branch $branch"
git checkout -b $branch

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to create branch. Aborting." -ForegroundColor Red
    exit $LASTEXITCODE
}

if (Test-Path .\commit_changes.ps1) {
    Write-Host "Running commit helper..."
    & .\commit_changes.ps1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Commit helper failed. Resolve issues and run this script again." -ForegroundColor Red
        exit $LASTEXITCODE
    }
} else {
    Write-Host "commit_changes.ps1 not found — running manual git add/commit"
    git add -A
    git commit -m "Mobile: make app customer-only; enforce mobile API permissions; add idempotency" || exit $LASTEXITCODE
}

Write-Host "Pushing branch to origin..."
git push -u origin $branch
if ($LASTEXITCODE -ne 0) {
    Write-Host "Push failed. Check remote and authentication." -ForegroundColor Red
    exit $LASTEXITCODE
}

if (Get-Command gh -ErrorAction SilentlyContinue) {
    Write-Host "Creating PR with gh..."
    gh pr create --fill --base main || Write-Host "gh pr create failed; create PR manually." -ForegroundColor Yellow
} else {
    Write-Host "gh CLI not available. Create a PR from branch $branch on your remote." -ForegroundColor Yellow
}

Write-Host "Done. Open the PR for review." -ForegroundColor Green
