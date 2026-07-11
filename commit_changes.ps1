# Commit helper for StayLux changes — run from repository root
Write-Host "Preparing to commit StayLux changes..."
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "git not found in PATH. Install git or run these commands manually:" -ForegroundColor Yellow
    Write-Host "git rm --cached web/db.sqlite3 2>$null || true"
    Write-Host "git add -A"
    Write-Host "git commit -m 'Mobile: make app customer-only; enforce mobile API permissions; redact admin fields; add idempotency guards and tests'"
    Write-Host "git push origin HEAD"
    exit 1
}

git rm --cached web/db.sqlite3 2>$null || Write-Host "web/db.sqlite3 not tracked or already removed"
git add -A
$msg = "Mobile: make app customer-only; enforce mobile API permissions; redact admin fields; add idempotency guards and tests"
git commit -m $msg
if ($LASTEXITCODE -ne 0) {
    Write-Host "Commit failed — inspect git status and try again." -ForegroundColor Red
    exit $LASTEXITCODE
}
git push origin HEAD
Write-Host "Push complete. Create PR from the pushed branch in your remote repository." -ForegroundColor Green
