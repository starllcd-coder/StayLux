from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    # Auth
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Rooms / Units (Inventory)
    path("rooms/", views.units_list, name="units_list"),
    path("rooms/new/", views.unit_create, name="unit_create"),
    path("rooms/<int:pk>/edit/", views.unit_edit, name="unit_edit"),
    path("rooms/<int:pk>/delete/", views.unit_delete, name="unit_delete"),

    # Unit Types (optional, needed for rooms)
    path("room-types/", views.unit_types_list, name="unit_types_list"),
    path("room-types/new/", views.unit_type_create, name="unit_type_create"),
    path("room-types/<int:pk>/edit/", views.unit_type_edit, name="unit_type_edit"),
    path("room-types/<int:pk>/delete/", views.unit_type_delete, name="unit_type_delete"),
    path("room-types/<int:pk>/amenities/", views.unit_type_amenities, name="unit_type_amenities"),

    # Bookings
    path("bookings/", views.bookings_list, name="bookings_list"),
    path("bookings/group/<int:pk>/agreement/", views.booking_agreement_print, name="booking_agreement_print"),

    # ✅ NEW: Booking Wizard
    path("bookings/wizard/", views.booking_wizard_start, name="booking_wizard_start"),
    path("bookings/wizard/cancel/", views.booking_wizard_cancel, name="booking_wizard_cancel"),
    path("bookings/wizard/step-1/", views.booking_wizard_step1, name="booking_wizard_step1"),
    path("bookings/wizard/step-2/", views.booking_wizard_step2, name="booking_wizard_step2"),
    path("bookings/wizard/step-3/", views.booking_wizard_step3, name="booking_wizard_step3"),
    path("bookings/wizard/step-4/", views.booking_wizard_step4, name="booking_wizard_step4"),

    # Old single-form create (kept)
    path("bookings/new/", views.booking_create, name="booking_create"),
    path("bookings/<int:pk>/edit/", views.booking_edit, name="booking_edit"),
    path("bookings/<int:pk>/delete/", views.booking_delete, name="booking_delete"),
    path("bookings/<int:pk>/action/", views.booking_action, name="booking_action"),
    path("bookings/<int:pk>/checkout/info/", views.booking_checkout_info, name="booking_checkout_info"),
    path("bookings/<int:pk>/checkout/invoice/", views.booking_checkout_invoice, name="booking_checkout_invoice"),
    path("bookings/<int:pk>/checkout/", views.booking_checkout, name="booking_checkout"),
    path("bookings/<int:pk>/checkout/whatsapp/", views.booking_checkout_whatsapp, name="booking_checkout_whatsapp"),

    # Guests
    path("guests/", views.guests_list, name="guests_list"),
    path("guests/new/", views.guest_create, name="guest_create"),
    path("guests/<int:pk>/edit/", views.guest_edit, name="guest_edit"),
    path("guests/<int:pk>/delete/", views.guest_delete, name="guest_delete"),
    path("guests/<int:pk>/upload-id/", views.guest_id_upload, name="guest_id_upload"),
    path("guests/<int:pk>/view-id/", views.guest_id_view, name="guest_id_view"),
    path("guests/report/print/", views.guests_report_print, name="guests_report_print"),
    path("guests/export/pdf/", views.guests_export_pdf, name="guests_export_pdf"),
    path("guests/export/excel/", views.guests_export_excel, name="guests_export_excel"),

    # Maintenance
    path("maintenance/", views.maintenance_list, name="maintenance_list"),
    path("maintenance/new/", views.maintenance_create, name="maintenance_create"),
    path("maintenance/<int:pk>/edit/", views.maintenance_edit, name="maintenance_edit"),
    path("maintenance/<int:pk>/complete/", views.maintenance_complete, name="maintenance_complete"),
    path("maintenance/<int:pk>/delete/", views.maintenance_delete, name="maintenance_delete"),

    # Housekeeping
    path("housekeeping/", views.housekeeping_list, name="housekeeping_list"),
    path("housekeeping/<int:pk>/action/", views.housekeeping_action, name="housekeeping_action"),

    # Billing (Invoices)
    path("billing/invoices/", views.invoices_list, name="invoices_list"),
    path("billing/invoices/new/", views.invoice_create, name="invoice_create"),
    path("billing/invoices/<int:pk>/edit/", views.invoice_edit, name="invoice_edit"),
    path("billing/invoices/<int:pk>/delete/", views.invoice_delete, name="invoice_delete"),
    path("billing/invoices/<int:pk>/print/", views.invoice_print_view, name="invoice_print"),
    path("billing/", views.billing_overview, name="billing_overview"),

    # Payments
    path("billing/payments/", views.payments_list, name="payments_list"),
    path("billing/payments/report/print/", views.payments_report_print, name="payments_report_print"),
    path("billing/payments/report/pdf/", views.payments_report_pdf, name="payments_report_pdf"),
    path("billing/payments/report/excel/", views.payments_report_excel, name="payments_report_excel"),
    path("billing/payments/new/", views.payment_create, name="payment_create"),
    path("billing/payments/<int:pk>/edit/", views.payment_edit, name="payment_edit"),
    path("billing/payments/<int:pk>/delete/", views.payment_delete, name="payment_delete"),

    # Pricing
    path("pricing/rate-plans/", views.rateplans_list, name="rateplans_list"),
    path("pricing/seasonal-rates/", views.seasonalrates_list, name="seasonalrates_list"),

    # Reports
    path("reports/", views.reports_home, name="reports_home"),
    path("reports/bookings/print/", views.bookings_report_print, name="bookings_report_print"),
    path("reports/occupancy/print/", views.occupancy_report_print, name="occupancy_report_print"),
    path("reports/occupancy/pdf/", views.occupancy_report_pdf, name="occupancy_report_pdf"),
    path("reports/occupancy/excel/", views.occupancy_report_excel, name="occupancy_report_excel"),
    path("reports/revenue/print/", views.revenue_report_print, name="revenue_report_print"),
    path("reports/revenue/pdf/", views.revenue_report_pdf, name="revenue_report_pdf"),
    path("reports/revenue/excel/", views.revenue_report_excel, name="revenue_report_excel"),
    path("reports/maintenance/print/", views.maintenance_report_print, name="maintenance_report_print"),
    path("reports/maintenance/pdf/", views.maintenance_report_pdf, name="maintenance_report_pdf"),
    path("reports/maintenance/excel/", views.maintenance_report_excel, name="maintenance_report_excel"),

    # Settings
    path("settings/", views.settings_page, name="settings_page"),
    path("settings/property/switch/", views.switch_active_property, name="switch_active_property"),
    path("settings/staff/", views.staff_list, name="staff_list"),
    path("settings/staff/new/", views.staff_create, name="staff_create"),
    path("settings/staff/<int:pk>/edit/", views.staff_edit, name="staff_edit"),
    path("settings/staff/<int:pk>/delete/", views.staff_delete, name="staff_delete"),
    path("settings/owners/", views.owners_list, name="owners_list"),
    path("settings/owners/new/", views.owner_create, name="owner_create"),
    path("settings/owners/<int:pk>/edit/", views.owner_edit, name="owner_edit"),
    path("settings/owners/<int:pk>/delete/", views.owner_delete, name="owner_delete"),
]
