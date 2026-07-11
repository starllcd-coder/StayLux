Title: Mobile app — customer-only, mobile API hardening, serializer and idempotency fixes

Summary:
- Clarify mobile app is customer-only (`mobile/README.md`).
- Mobile API permission enforcement: added/ensured `permission_classes` using `IsMobileCustomer` or `IsAuthenticatedOrMobileReadOnly` where appropriate (multiple `web/mobile_api/*` views).
- Redacted admin/internal fields from mobile serializers:
  - `web/mobile_api/bookings/serializers.py` — replaced `unit` with `unit_id`.
  - `web/mobile_api/discovery/serializers.py` — removed `status` from `UnitListSerializer`.
- Added idempotency safeguards in mobile booking/payment flows:
  - `web/mobile_api/bookings/services.py` — return existing booking if same customer/unit/check-in/check-out exists; reuse pending `MobilePaymentRecord` for duplicate payment intents.
- Tests added:
  - `web/mobile_api/tests/test_permissions.py` — unit tests for `IsMobileCustomer`.
  - `web/core/tests/test_mobile_access.py` — integration test asserting non-staff users are redirected from staff booking list.

Notes / Remaining recommendations (not implemented here):
- Full payment provider integration (gateway webhooks + secure provider validations).
- Explicit idempotency-key schema (DB model + migration) for robust duplicate prevention.
- Additional integration tests verifying mobile users cannot access broader staff endpoints; expand test coverage.
- Create a PR and run full CI/test suite in CI or local environment.

Suggested local commands to commit & push these changes (run from repository root):

```powershell
git rm --cached web/db.sqlite3 2>$null || true
git add -A
git commit -m "Mobile: make app customer-only; enforce mobile API permissions; redact admin fields; add idempotency guards and tests"
git push origin HEAD
```

If you want, I can also create a small migration and add an `idempotency_key` model+field. Say "add idempotency DB model" to proceed.
