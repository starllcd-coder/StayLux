# StayLux – Full Multi-Platform Project Structure

This ZIP contains a clean scaffold for:
- **Web**: Django + HTML templates + DRF API (API-first so Desktop/Mobile share the same backend)
- **Desktop**: Python + PySide6 client (talks to API)
- **Mobile**: Flutter app (iOS/Android) client (talks to API)
- **Docs**: One place for requirements, design system, and workflows

## What you need to do next
1) Put your premium brand assets into: `assets/brand/` (logo, icons, etc.)
2) Create a Python venv and run the Django server (instructions inside `web/README.md`)
3) Start implementing modules in this order:
   - settings/property profile, auth/roles
   - inventory (types/amenities, rooms/units)
   - bookings wizard + guests + documents
   - housekeeping + maintenance
   - apartments contracts + monthly invoices
   - reports + exports
   - owner portal

> Note: SQLite is set by default for development. Switching to PostgreSQL is a settings/env change.
