#!/usr/bin/env pwsh
# Helper: untrack local sqlite DB from git index
Write-Host "This will remove web/db.sqlite3 from git index (won't delete the file)."
git rm --cached web/db.sqlite3
if ($LASTEXITCODE -ne 0) {
  Write-Error "git rm failed with exit code $LASTEXITCODE"
  exit $LASTEXITCODE
}
git commit -m "Stop tracking local sqlite DB (web/db.sqlite3)" || Write-Host "Commit skipped (no changes)"
Write-Host "Done."
