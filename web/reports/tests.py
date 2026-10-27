from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import OwnerProfile
from billing.models import Invoice, Payment
from bookings.models import Booking, BookingStatus
from maintenance.models import MaintenanceRequest
from guests.models import Guest
from inventory.models import Unit, UnitType
from reports.services import bookings_kpis, calc_occupancy
from settings_app.models import PropertyProfile


class ReportServiceTests(TestCase):
    def setUp(self) -> None:
        self.property = PropertyProfile.objects.create(name_en="Report Property")
        self.unit_type = UnitType.objects.create(
            property_profile=self.property,
            business_type=self.property.business_type,
            name_en="Standard",
            base_rate=Decimal("10.000"),
        )
        self.unit = Unit.objects.create(
            property_profile=self.property,
            unit_type=self.unit_type,
            code="R-1",
            daily_price=Decimal("20.000"),
            monthly_price=Decimal("300.000"),
        )
        self.guest = Guest.objects.create(
            property_profile=self.property,
            business_type=self.property.business_type,
            full_name="Report Guest",
        )

    def test_calc_occupancy_uses_start_end_date_overlap(self):
        Booking.objects.create(
            property_profile=self.property,
            guest=self.guest,
            unit=self.unit,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 4),
        )

        report = calc_occupancy(self.property.id, date(2026, 3, 1), date(2026, 3, 3))

        self.assertEqual(report["booked_nights"], 3)
        self.assertEqual(report["occupancy_pct"], 100)

    def test_bookings_kpis_revenue_uses_estimate_total_and_excludes_cancelled(self):
        Booking.objects.create(
            property_profile=self.property,
            guest=self.guest,
            unit=self.unit,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 3),
            rate=Decimal("10.000"),
            discount=Decimal("0.000"),
            status=BookingStatus.RESERVED,
        )
        Booking.objects.create(
            property_profile=self.property,
            guest=self.guest,
            unit=self.unit,
            start_date=date(2026, 3, 3),
            end_date=date(2026, 3, 5),
            rate=Decimal("99.000"),
            discount=Decimal("0.000"),
            status=BookingStatus.CANCELLED,
        )

        kpis = bookings_kpis(self.property.id, date(2026, 3, 1), date(2026, 3, 4))

        self.assertEqual(kpis["total_bookings"], 2)
        self.assertEqual(kpis["by_status"].get(BookingStatus.RESERVED), 1)
        self.assertEqual(kpis["by_status"].get(BookingStatus.CANCELLED), 1)
        self.assertEqual(kpis["revenue_estimated"], "20.000")


class OwnerDashboardScopeTests(TestCase):
    def test_owner_report_controls_periods_and_scoped_unit_labels(self):
        self.client.force_login(self.owner_user)
        for period, label in [("daily", "Daily Report"), ("weekly", "Weekly Report"), ("monthly", "Monthly Report")]:
            response = self.client.get("/owner/", {"period": period})
            self.assertContains(response, label)
            self.assertContains(response, "Print Report")
            self.assertContains(response, "window.print()")
            self.assertContains(response, self.unit_1.code)
            self.assertNotContains(response, self.unit_2.code)
            self.assertNotContains(response, "View dashboard JSON")
            self.assertEqual(response.context["selected_period"], period)
        response = self.client.post("/logout/")
        self.assertRedirects(response, "/login/")
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.get("/owner/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/login/"))

    @override_settings(ALLOWED_HOSTS=["localhost", "127.0.0.1"])
    def test_owner_html_dashboard_works_with_production_host_checks(self):
        self.client.force_login(self.owner_user)
        response = self.client.get("/owner/", HTTP_HOST="localhost")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["dashboard"]["units"]["total_units"], 1)
        self.assertNotContains(response, "Dashboard not available")

    def test_owner_html_dashboard_includes_checked_out_bookings(self):
        today = timezone.localdate()
        self.booking_a.start_date = today - timedelta(days=1)
        self.booking_a.end_date = today
        self.booking_a.status = "checked_out"
        self.booking_a.save()
        Invoice.objects.create(
            property_profile=self.property, booking=self.booking_a, guest=self.guest_a,
            total=Decimal("100.000"), balance_due=Decimal("20.000"),
        )
        self.client.force_login(self.owner_user)
        response = self.client.get("/owner/?period=weekly")
        self.assertEqual(response.status_code, 200)
        dashboard = response.context["dashboard"]
        self.assertEqual(dashboard["occupancy"]["booked_nights"], 1)
        self.assertEqual(dashboard["occupancy"]["total_unit_nights"], 7)
        self.assertEqual(dashboard["billing"]["revenue_total"], "100.000")

    def setUp(self) -> None:
        self.client = Client()
        User = get_user_model()

        self.property = PropertyProfile.objects.create(name_en="Owner Report Property")
        self.unit_type = UnitType.objects.create(
            property_profile=self.property,
            business_type=self.property.business_type,
            name_en="Standard",
            base_rate=Decimal("10.000"),
        )
        self.unit_1 = Unit.objects.create(
            property_profile=self.property,
            unit_type=self.unit_type,
            code="A-101",
            daily_price=Decimal("20.000"),
            monthly_price=Decimal("300.000"),
        )
        self.unit_2 = Unit.objects.create(
            property_profile=self.property,
            unit_type=self.unit_type,
            code="A-102",
            daily_price=Decimal("20.000"),
            monthly_price=Decimal("300.000"),
        )

        self.owner_user = User.objects.create_user(username="owner_a", password="pass1234")
        self.owner_profile = OwnerProfile.objects.create(user=self.owner_user, property=self.property, is_active=True)
        self.owner_profile.units.add(self.unit_1)

        self.other_owner_user = User.objects.create_user(username="owner_b", password="pass1234")
        self.other_owner_profile = OwnerProfile.objects.create(user=self.other_owner_user, property=self.property, is_active=True)
        self.other_owner_profile.units.add(self.unit_2)

        self.guest_a = Guest.objects.create(
            property_profile=self.property,
            business_type=self.property.business_type,
            full_name="Guest A",
        )
        self.guest_b = Guest.objects.create(
            property_profile=self.property,
            business_type=self.property.business_type,
            full_name="Guest B",
        )

        self.booking_a = Booking.objects.create(
            property_profile=self.property,
            guest=self.guest_a,
            unit=self.unit_1,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 4),
            rate=Decimal("50.000"),
        )
        self.booking_b = Booking.objects.create(
            property_profile=self.property,
            guest=self.guest_b,
            unit=self.unit_2,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 4),
            rate=Decimal("50.000"),
        )

    def test_owner_dashboard_only_returns_assigned_unit_metrics(self):
        invoice_a = Invoice.objects.create(
            property_profile=self.property,
            booking=self.booking_a,
            guest=self.guest_a,
            total=Decimal("100.000"),
            balance_due=Decimal("20.000"),
        )
        Payment.objects.create(
            invoice=invoice_a,
            property_profile=self.property,
            amount=Decimal("80.000"),
        )
        MaintenanceRequest.objects.create(
            property_profile=self.property,
            unit=self.unit_1,
            total_cost=Decimal("10.000"),
            title="Owner A Cost",
        )

        invoice_b = Invoice.objects.create(
            property_profile=self.property,
            booking=self.booking_b,
            guest=self.guest_b,
            total=Decimal("999.000"),
            balance_due=Decimal("0.000"),
        )
        Payment.objects.create(
            invoice=invoice_b,
            property_profile=self.property,
            amount=Decimal("999.000"),
        )
        MaintenanceRequest.objects.create(
            property_profile=self.property,
            unit=self.unit_2,
            total_cost=Decimal("77.000"),
            title="Owner B Cost",
        )

        self.client.login(username="owner_a", password="pass1234")
        res = self.client.get("/api/reports/owner-dashboard/?period=monthly")

        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload["units"]["total_units"], 1)
        self.assertEqual(payload["billing"]["revenue_total"], "100.000")
        self.assertEqual(payload["billing"]["collections_total"], "80.000")
        self.assertEqual(payload["billing"]["outstanding_total"], "20.000")
        self.assertEqual(payload["maintenance"]["total_cost"], "10.000")
        self.assertEqual(payload["billing"]["net_income_total"], "90.000")

    def test_owner_dashboard_period_filter_daily_excludes_older_records(self):
        invoice = Invoice.objects.create(
            property_profile=self.property,
            booking=self.booking_a,
            guest=self.guest_a,
            total=Decimal("100.000"),
            balance_due=Decimal("0.000"),
        )
        old_invoice = Invoice.objects.create(
            property_profile=self.property,
            booking=self.booking_a,
            guest=self.guest_a,
            total=Decimal("50.000"),
            balance_due=Decimal("0.000"),
        )
        Payment.objects.create(
            invoice=invoice,
            property_profile=self.property,
            amount=Decimal("100.000"),
        )
        old_payment = Payment.objects.create(
            invoice=old_invoice,
            property_profile=self.property,
            amount=Decimal("50.000"),
        )
        MaintenanceRequest.objects.create(
            property_profile=self.property,
            unit=self.unit_1,
            total_cost=Decimal("10.000"),
            title="Today Cost",
        )
        old_maintenance = MaintenanceRequest.objects.create(
            property_profile=self.property,
            unit=self.unit_1,
            total_cost=Decimal("5.000"),
            title="Old Cost",
        )

        old_ts = timezone.make_aware(datetime(2026, 1, 1, 10, 0, 0))
        old_invoice.__class__.objects.filter(pk=old_invoice.pk).update(created_at=old_ts)
        old_payment.__class__.objects.filter(pk=old_payment.pk).update(created_at=old_ts)
        old_maintenance.__class__.objects.filter(pk=old_maintenance.pk).update(created_at=old_ts)

        self.client.login(username="owner_a", password="pass1234")
        res = self.client.get("/api/reports/owner-dashboard/?period=daily")

        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertEqual(payload["billing"]["revenue_total"], "100.000")
        self.assertEqual(payload["billing"]["collections_total"], "100.000")
        self.assertEqual(payload["maintenance"]["total_cost"], "10.000")

    def test_owner_dashboard_rejects_non_owner_users(self):
        get_user_model().objects.create_user(username="staff_only", password="pass1234")
        self.client.login(username="staff_only", password="pass1234")
        res = self.client.get("/api/reports/owner-dashboard/?period=monthly")
        self.assertEqual(res.status_code, 403)

    def test_owner_cannot_open_property_level_reports_endpoint(self):
        self.client.login(username="owner_a", password="pass1234")
        res = self.client.get(f"/api/reports/dashboard/?property_profile={self.property.id}")
        self.assertEqual(res.status_code, 403)
