# StayLux Web (Django + Templates + DRF)

## Setup
1) Create venv:
   - Windows: `python -m venv .venv && .venv\Scripts\activate`
   - Linux/Mac: `python -m venv .venv && source .venv/bin/activate`
2) Install:
   - `pip install -r requirements.txt`
3) Run migrations:
   - `python manage.py migrate`
4) Create admin:
   - `python manage.py createsuperuser`
5) Run:
   - `python manage.py runserver`

## Apps (planned)
- core (base models, utilities)
- accounts (roles/permissions)
- settings_app (property profile, owner portal settings)
- inventory (types, amenities, rooms/units)
- bookings (bookings wizard, check-in/out)
- guests (guest profiles + ID documents)
- housekeeping (tasks)
- maintenance (tickets + before/after photos)
- contracts (apartment monthly contracts)
- invoices (monthly invoices + payments)
- reports (PDF/Excel exports)
- owner_portal (owner views + permissions enforcement)
