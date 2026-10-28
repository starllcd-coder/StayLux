# StayLux roles

Property employees use StaffProfile roles. Individual apartment owners use
OwnerProfile and are not property administrators.

| Role | Intended responsibility |
| --- | --- |
| Owner/Admin (`owner_admin`) | Property administration, employees/owners, operations, billing and reporting |
| Manager (`manager`) | Manage the assigned property's operations, employees/owners, billing and reporting; edit/delete that property through confirmation |
| Accounts (`accounts`) | Invoices, payments, receipts, finance/occupancy/cost reports and exports for the assigned property |
| Reception (`reception`) | Guests, bookings, check-in/out and routine billing |
| Housekeeping (`housekeeping`) | Housekeeping jobs and job notifications |
| Maintenance (`maintenance`) | Maintenance jobs and job notifications |
| Apartment owner (OwnerProfile) | Dashboard/reports for assigned apartments only |

Accounts cannot edit/delete properties, create or alter bookings/guests/units,
manage staff/owners, change pricing, or modify housekeeping/maintenance jobs.
Accounts cannot delete invoices/payments, void records, or invoke invoice refund
actions. These sensitive finance actions require Owner/Admin or Manager; routine
Reception permissions are otherwise preserved. Basic API lookup data remains
readable to active staff where needed for their workflows.

The web Accounts dashboard opens Reports. The sidebar shows billing and reports,
and invoice/payment forms omit void controls. Property selection is pinned to
the employee's assigned property; foreign invoice, guest and booking references
are rejected by billing APIs.

The owner/admin Flutter app recognizes `accounts` on login and grants access to
its existing financial dashboard and reports, notifications and personal app
settings. Staff, security, reservation and operational job management routes are
not granted to Accounts. Invoice/payment entry remains available through the web
app; this change does not add new mobile billing-entry screens.

## Assigning Accounts

In Settings > Employees, add or edit an employee and choose **Accounts** in Role.
Changes apply to backend permissions immediately. Sign in again on the mobile
app to refresh its cached role and menus.

Run `python manage.py migrate` when deploying. The role migration adds an enum
choice and does not change existing employee assignments. Deploy the updated
backend and rebuild the mobile app for the new menu permissions. Flutter/device
validation still requires a Flutter-equipped build machine.
