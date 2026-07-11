from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from accounts.models import OwnerProfile
from billing.models import Invoice
from bookings.models import Booking, BookingGroup, BookingType, RentCycle, is_unit_available
from core.forms import OwnerCreateForm, OwnerEditForm
from guests.models import Guest
from inventory.models import Unit, UnitType
from settings_app.models import BusinessType, PropertyProfile


class BookingFlowTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(username="tester", password="pass1234")

    def _create_property_bundle(self, business_type: str, code: str) -> dict:
        prop = PropertyProfile.objects.create(
            business_type=business_type,
            name_en=f"{business_type.title()} Property",
        )
        unit_type = UnitType.objects.create(
            property_profile=prop,
            business_type=business_type,
            name_en="Standard",
            base_rate=Decimal("10.000"),
            is_active=True,
        )
        unit = Unit.objects.create(
            property_profile=prop,
            unit_type=unit_type,
            code=code,
            daily_price=Decimal("20.000"),
            monthly_price=Decimal("300.000"),
        )
        guest = Guest.objects.create(
            property_profile=prop,
            full_name="Guest One",
        )
        return {"property": prop, "unit": unit, "guest": guest}

    def test_hotel_booking_availability(self) -> None:
        bundle = self._create_property_bundle(BusinessType.HOTEL, "101")
        booking = Booking.objects.create(
            property_profile=bundle["property"],
            guest=bundle["guest"],
            unit=bundle["unit"],
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 5),
            booking_type=BookingType.HOTEL,
            rent_cycle=RentCycle.NIGHTLY,
        )
        self.assertIsNotNone(booking.id)
        self.assertFalse(
            is_unit_available(bundle["unit"].id, date(2026, 2, 3), date(2026, 2, 4))
        )
        self.assertTrue(
            is_unit_available(bundle["unit"].id, date(2026, 2, 6), date(2026, 2, 7))
        )

    def test_apartment_booking_availability(self) -> None:
        bundle = self._create_property_bundle(BusinessType.APARTMENTS, "A-01")
        booking = Booking.objects.create(
            property_profile=bundle["property"],
            guest=bundle["guest"],
            unit=bundle["unit"],
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
            booking_type=BookingType.APARTMENT,
            rent_cycle=RentCycle.MONTHLY,
        )
        self.assertIsNotNone(booking.id)
        self.assertFalse(
            is_unit_available(bundle["unit"].id, date(2026, 2, 10), date(2026, 2, 12))
        )
        self.assertTrue(
            is_unit_available(bundle["unit"].id, date(2026, 3, 2), date(2026, 3, 5))
        )

    def test_booking_wizard_defaults_hotel(self) -> None:
        bundle = self._create_property_bundle(BusinessType.HOTEL, "102")
        client = Client()
        client.login(username="tester", password="pass1234")
        session = client.session
        session["active_property_id"] = bundle["property"].id
        session.save()

        response = client.get("/bookings/wizard/")
        self.assertEqual(response.status_code, 302)
        state = client.session.get("booking_wizard_state")
        self.assertIsNotNone(state)
        self.assertEqual(state.get("booking_type"), BookingType.HOTEL)
        self.assertEqual(state.get("rent_cycle"), RentCycle.NIGHTLY)

    def test_booking_wizard_defaults_apartments(self) -> None:
        bundle = self._create_property_bundle(BusinessType.APARTMENTS, "A-02")
        client = Client()
        client.login(username="tester", password="pass1234")
        session = client.session
        session["active_property_id"] = bundle["property"].id
        session.save()

        response = client.get("/bookings/wizard/")
        self.assertEqual(response.status_code, 302)
        state = client.session.get("booking_wizard_state")
        self.assertIsNotNone(state)
        self.assertEqual(state.get("booking_type"), BookingType.APARTMENT)
        self.assertEqual(state.get("rent_cycle"), RentCycle.MONTHLY)


class BookingWizardActionTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(username="wizard", password="pass1234")
        self.client = Client()
        self.client.login(username="wizard", password="pass1234")

    def _create_apartment_bundle(self) -> dict:
        prop = PropertyProfile.objects.create(
            business_type=BusinessType.APARTMENTS,
            name_en="Apartments Property",
        )
        unit_type = UnitType.objects.create(
            property_profile=prop,
            business_type=BusinessType.APARTMENTS,
            name_en="Standard",
            base_rate=Decimal("10.000"),
            is_active=True,
        )
        unit = Unit.objects.create(
            property_profile=prop,
            unit_type=unit_type,
            code="A-101",
            daily_price=Decimal("20.000"),
            monthly_price=Decimal("300.000"),
        )
        guest = Guest.objects.create(
            property_profile=prop,
            business_type=BusinessType.APARTMENTS,
            full_name="Guest One",
        )
        return {"property": prop, "unit": unit, "guest": guest}

    def _set_wizard_state(self, prop: PropertyProfile, unit: Unit, guest: Guest) -> None:
        session = self.client.session
        session["active_property_id"] = prop.id
        session["booking_wizard_state"] = {
            "step": 3,
            "start_date": "2026-02-01",
            "end_date": "2026-03-01",
            "unit_ids": [unit.id],
            "guest_id": guest.id,
            "booking_type": BookingType.APARTMENT,
            "rent_cycle": RentCycle.MONTHLY,
            "adults": 1,
            "children": 0,
        }
        session.save()

    def _post_step4(self, action: str):
        return self.client.post(
            "/bookings/wizard/step-4/",
            {
                "discount": "0",
                "advance_payment": "0",
                "payment_method": "cash",
                "notes": "",
                "action": action,
                "open_new_tab": "1",
            },
        )

    def test_print_receipt_redirects_to_print_view(self) -> None:
        bundle = self._create_apartment_bundle()
        self._set_wizard_state(bundle["property"], bundle["unit"], bundle["guest"])

        response = self._post_step4("print_receipt")

        invoice = Invoice.objects.get(property_profile=bundle["property"])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"/billing/invoices/{invoice.id}/print/?print=1")
        self.assertTrue(Booking.objects.filter(property_profile=bundle["property"]).exists())

    def test_save_receipt_redirects_to_pdf_view(self) -> None:
        bundle = self._create_apartment_bundle()
        self._set_wizard_state(bundle["property"], bundle["unit"], bundle["guest"])

        response = self._post_step4("save_pdf")

        invoice = Invoice.objects.get(property_profile=bundle["property"])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"/billing/invoices/{invoice.id}/print/")
        self.assertTrue(Booking.objects.filter(property_profile=bundle["property"]).exists())

    def test_print_agreement_redirects_to_print_view(self) -> None:
        bundle = self._create_apartment_bundle()
        self._set_wizard_state(bundle["property"], bundle["unit"], bundle["guest"])

        response = self._post_step4("print_agreement")

        group = BookingGroup.objects.get(property_profile=bundle["property"])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"/bookings/group/{group.id}/agreement/?print=1")
        self.assertTrue(Invoice.objects.filter(property_profile=bundle["property"]).exists())

    def test_save_agreement_redirects_to_pdf_view(self) -> None:
        bundle = self._create_apartment_bundle()
        self._set_wizard_state(bundle["property"], bundle["unit"], bundle["guest"])

        response = self._post_step4("save_agreement")

        group = BookingGroup.objects.get(property_profile=bundle["property"])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"/bookings/group/{group.id}/agreement/")
        self.assertTrue(Invoice.objects.filter(property_profile=bundle["property"]).exists())


class OwnerAssignmentValidationTests(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.prop = PropertyProfile.objects.create(name_en="Owner Property")
        self.unit_type = UnitType.objects.create(
            property_profile=self.prop,
            business_type=self.prop.business_type,
            name_en="Standard",
            base_rate=Decimal("10.000"),
        )
        self.unit_1 = Unit.objects.create(
            property_profile=self.prop,
            unit_type=self.unit_type,
            code="U-101",
            daily_price=Decimal("20.000"),
            monthly_price=Decimal("300.000"),
        )
        self.unit_2 = Unit.objects.create(
            property_profile=self.prop,
            unit_type=self.unit_type,
            code="U-102",
            daily_price=Decimal("20.000"),
            monthly_price=Decimal("300.000"),
        )

        self.owner_a_user = User.objects.create_user(username="owner_form_a", password="pass1234")
        self.owner_a = OwnerProfile.objects.create(user=self.owner_a_user, property=self.prop, is_active=True)
        self.owner_a.units.add(self.unit_1)

        self.owner_b_user = User.objects.create_user(username="owner_form_b", password="pass1234")
        self.owner_b = OwnerProfile.objects.create(user=self.owner_b_user, property=self.prop, is_active=True)
        self.owner_b.units.add(self.unit_2)

    def test_owner_create_form_rejects_already_assigned_unit(self):
        form = OwnerCreateForm(
            data={
                "username": "owner_new",
                "password": "pass1234",
                "units": [self.unit_1.id],
                "is_active": True,
            },
            property_obj=self.prop,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("units", form.errors)

    def test_owner_edit_form_allows_keeping_current_units(self):
        form = OwnerEditForm(
            data={
                "first_name": "Owner",
                "last_name": "A",
                "email": "ownera@example.com",
                "units": [self.unit_1.id],
                "is_active": True,
            },
            property_obj=self.prop,
            owner_instance=self.owner_a,
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_owner_edit_form_rejects_unit_owned_by_other_owner(self):
        form = OwnerEditForm(
            data={
                "first_name": "Owner",
                "last_name": "A",
                "email": "ownera@example.com",
                "units": [self.unit_2.id],
                "is_active": True,
            },
            property_obj=self.prop,
            owner_instance=self.owner_a,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("units", form.errors)


class OwnerPortalAccessTests(TestCase):
    def test_owner_portal_rejects_non_owner(self):
        User = get_user_model()
        User.objects.create_user(username="plain_user", password="pass1234")
        client = Client()
        client.login(username="plain_user", password="pass1234")
        response = client.get("/owner/")
        self.assertEqual(response.status_code, 403)


class GuestsListTests(TestCase):
    def test_guests_list_includes_guest_without_booking(self) -> None:
        user = get_user_model().objects.create_superuser(
            username="guest_admin",
            password="pass1234",
            email="guest_admin@example.com",
        )
        prop = PropertyProfile.objects.create(
            business_type=BusinessType.APARTMENTS,
            name_en="Guests Property",
        )
        Guest.objects.create(
            property_profile=prop,
            business_type=BusinessType.APARTMENTS,
            full_name="New Guest Without Booking",
        )

        client = Client()
        client.force_login(user)
        session = client.session
        session["active_property_id"] = prop.id
        session.save()

        response = client.get("/guests/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "New Guest Without Booking")
