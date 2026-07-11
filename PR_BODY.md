Title: Mobile: enforce customer-only mobile API, serializers, and idempotency

Summary
- Make the mobile app customer-only; enforce `IsMobileCustomer` on mobile endpoints.
- Redact admin/internal fields from mobile serializers.
- Add idempotency support for mobile bookings and payment placeholders via `MobileIdempotencyKey` model and service wiring.
- Add unit and integration tests for permissions and idempotency.

Files changed (high level)
- web/core/views.py (converted inline role guards to decorators)
- web/mobile_api/bookings/serializers.py (added `idempotency_key` and `unit_id` usage)
- web/mobile_api/discovery/serializers.py (redacted admin fields)
- web/mobile_api/bookings/models.py (added `MobileIdempotencyKey`)
- web/mobile_api/bookings/services.py (idempotency wiring + guest mapping)
- web/mobile_api/bookings/views.py (pass through `idempotency_key`)
- web/mobile_api/tests/test_permissions.py (added)
- web/core/tests/test_mobile_access.py (added)
- web/mobile_api/tests/test_idempotency.py (added)
- commit_changes.ps1, COMMIT_INSTRUCTIONS.md, commit_and_push.ps1 (helpers)

Testing
- I ran targeted tests locally: bookings service tests, mobile permission unit tests, mobile idempotency tests, and a staff-access integration test. They passed for the modified areas.

How to apply locally
1. Create a branch and run the commit helper (PowerShell):
```powershell
& .venv\Scripts\Activate.ps1
.\branch_and_pr.ps1
```

2. If `gh` is installed the script will attempt to open a PR; otherwise follow the printed instructions to create a PR manually.

Notes
- I did not push changes for you — run the helper locally to push and open the PR.
- Recommended follow-ups: run the full test suite in CI and review payment provider integration and webhook handling.
