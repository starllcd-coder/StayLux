from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from accounts.models import StaffProfile, StaffRole, OwnerProfile
from billing.models import Invoice, Payment
from bookings.models import Booking
from guests.models import Guest
from inventory.models import Unit, UnitType
from settings_app.models import PropertyProfile
from core.forms import StaffCreateForm
from core.permissions import _get_user_role


class AccountsRoleTests(TestCase):
    def setUp(self):
        self.prop = PropertyProfile.objects.create(name_en="Finance Property", business_type="apartments")
        self.other = PropertyProfile.objects.create(name_en="Other Property", business_type="apartments")
        self.user = get_user_model().objects.create_user(username="accountant", password="pass")
        StaffProfile.objects.create(user=self.user, property=self.prop, role=StaffRole.ACCOUNTS)
        self.guest = Guest.objects.create(property_profile=self.prop, full_name="Guest", business_type="apartments")
        self.foreign_guest = Guest.objects.create(property_profile=self.other, full_name="Other guest", business_type="apartments")
        self.invoice = Invoice.objects.create(property_profile=self.prop, guest=self.guest, total=100, balance_due=100)
        self.foreign_invoice = Invoice.objects.create(property_profile=self.other, guest=self.foreign_guest)
        self.client.force_login(self.user)

    def test_role_available_in_employee_form(self):
        self.assertIn(("accounts", "Accounts"), list(StaffCreateForm().fields["role"].choices))

    def test_finance_pages_and_reports_are_available(self):
        for route in ["invoices_list", "payments_list", "invoice_create", "payment_create", "reports_home"]:
            self.assertEqual(self.client.get(reverse(route)).status_code, 200, route)
        response = self.client.get(reverse("reports_home"))
        self.assertContains(response, reverse("payments_list"))
        self.assertNotContains(response, 'href="' + reverse("settings_page") + '"')

    def test_accounts_cannot_manage_property_staff_or_bookings(self):
        for route in ["settings_page", "staff_list", "owners_list", "booking_create", "unit_create", "maintenance_create"]:
            response = self.client.get(reverse(route))
            self.assertIn(response.status_code, [302, 403], route)
        self.assertEqual(self.client.post("/api/bookings/", {}).status_code, 403)
        self.assertEqual(self.client.post("/api/housekeeping/", {}).status_code, 403)
        self.assertEqual(self.client.post("/api/maintenance/", {}).status_code, 403)
        self.assertEqual(self.client.patch(f"/api/properties/{self.prop.pk}/", {"name_en": "changed"}, content_type="application/json").status_code, 403)

    def test_accounts_can_create_invoices_and_record_payments(self):
        response = self.client.post("/api/invoices/", {"guest": self.guest.pk, "property_profile": self.prop.pk, "status": "draft"})
        self.assertEqual(response.status_code, 201, response.content)
        response = self.client.post("/api/payments/", {
            "invoice": self.invoice.pk, "property_profile": self.prop.pk, "amount": "10.000", "method": "cash", "direction": "in",
        })
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Payment.objects.get().property_profile_id, self.prop.pk)

    def test_cannot_delete_void_or_refund_financial_records(self):
        self.assertEqual(self.client.delete(f"/api/invoices/{self.invoice.pk}/").status_code, 403)
        for action in ["void", "refund"]:
            self.assertEqual(self.client.post(f"/api/invoices/{self.invoice.pk}/{action}/", {}).status_code, 403)
        self.assertEqual(self.client.patch(f"/api/invoices/{self.invoice.pk}/", {"status": "void"}, content_type="application/json").status_code, 400)
        self.assertEqual(self.client.get(reverse("invoice_delete", args=[self.invoice.pk])).status_code, 403)
        self.assertTrue(Invoice.objects.filter(pk=self.invoice.pk).exists())

    def test_billing_and_reporting_are_scoped_to_assigned_property(self):
        session = self.client.session
        session["active_property_id"] = self.other.pk
        session.save()
        response = self.client.get(reverse("invoices_list"))
        self.assertEqual(response.context["prop"].pk, self.prop.pk)
        self.assertEqual(self.client.get(f"/api/invoices/{self.foreign_invoice.pk}/").status_code, 404)
        response = self.client.post("/api/payments/", {
            "invoice": self.foreign_invoice.pk, "property_profile": self.prop.pk, "amount": "10.000", "method": "cash",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(f"/api/reports/revenue/?property_profile={self.other.pk}").status_code, 403)
        self.assertEqual(self.client.get(f"/api/reports/revenue/?property_profile={self.prop.pk}").status_code, 200)

    def test_accounts_cannot_generate_invoice_from_foreign_booking(self):
        tier = UnitType.objects.create(property_profile=self.other, name_en="Standard", business_type="apartments")
        unit = Unit.objects.create(property_profile=self.other, unit_type=tier, code="X")
        booking = Booking.objects.create(property_profile=self.other, unit=unit, guest=self.foreign_guest,
            start_date=date.today(), end_date=date.today() + timedelta(days=1), rate=10, booking_type="apartment")
        response = self.client.post("/api/invoices/generate_from_booking/", {"booking": booking.pk})
        self.assertEqual(response.status_code, 404)

    def test_apartment_owner_is_not_an_operator_or_billing_staff(self):
        owner = get_user_model().objects.create_user(username="owner", password="pass")
        OwnerProfile.objects.create(user=owner, property=self.prop)
        self.assertEqual(_get_user_role(owner), "owner")
        self.client.force_login(owner)
        self.assertEqual(self.client.get("/api/invoices/").status_code, 403)
        self.assertEqual(self.client.post("/api/payments/", {}).status_code, 403)

    def test_inactive_accounts_user_cannot_access_finance(self):
        profile = self.user.staff_profile
        profile.is_active = False
        profile.save()
        self.assertEqual(self.client.get("/api/invoices/").status_code, 403)
