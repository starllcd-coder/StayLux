Commit instructions

Run these commands from the repository root (Windows PowerShell):

```powershell
& .venv\Scripts\Activate.ps1
.\commit_changes.ps1
```

If you prefer to run git commands manually:

```powershell
git rm --cached web/db.sqlite3 2>$null || true
git add -A
git commit -m "Mobile: make app customer-only; enforce mobile API permissions; redact admin fields; add idempotency guards and tests"
git push origin HEAD
```

Notes:
- This script assumes you will create a PR from the pushed branch on your remote.
- If `git` is not installed on your machine, install it or run the manual commands on a machine with git available.
