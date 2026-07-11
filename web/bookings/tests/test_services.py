from __future__ import annotations

import os
from datetime import date, timedelta
from decimal import Decimal

# Rely on the test runner to configure Django; avoid calling django.setup() at import time.
from django.test import TestCase

# Delay importing service and booking enums until runtime to avoid app registry errors



class BookingServiceTests(TestCase):
    def setUp(self) -> None:
        from django.apps import apps

        PropertyProfile = apps.get_model("settings_app", "PropertyProfile")
        Guest = apps.get_model("guests", "Guest")
        UnitType = apps.get_model("inventory", "UnitType")
        Unit = apps.get_model("inventory", "Unit")

        self.prop = PropertyProfile.objects.create(name_en="Test Property")
        self.unit_type = UnitType.objects.create(property_profile=self.prop, business_type=self.prop.business_type, name_en="Std", base_rate=Decimal("10.000"))
        self.unit1 = Unit.objects.create(property_profile=self.prop, unit_type=self.unit_type, code="R1", daily_price=Decimal("20.000"), monthly_price=Decimal("400.000"))
        self.unit2 = Unit.objects.create(property_profile=self.prop, unit_type=self.unit_type, code="R2", daily_price=Decimal("25.000"), monthly_price=Decimal("500.000"))
        self.guest = Guest.objects.create(property_profile=self.prop, business_type=self.prop.business_type, full_name="John Doe")

        self.start = date.today()
        self.end = self.start + timedelta(days=2)

    def test_create_group_and_bookings_without_advance(self):
        from bookings.services import create_booking_group_and_bookings
        from bookings.models import RentCycle, BookingType

        unit_rows = [{"unit": self.unit1, "rate": self.unit1.daily_price}, {"unit": self.unit2, "rate": self.unit2.daily_price}]
        state = {"start_date": self.start, "end_date": self.end, "adults": 2, "children": 0}

        group, bookings, inv = create_booking_group_and_bookings(
            property_profile=self.prop,
            guest=self.guest,
            unit_rows=unit_rows,
            state=state,
            rent_cycle=RentCycle.NIGHTLY,
            booking_type=BookingType.HOTEL,
            discount=Decimal("0.000"),
            advance=Decimal("0.000"),
            payment_method="cash",
            notes="",
        )

        self.assertIsNotNone(group.id)
        self.assertEqual(len(bookings), 2)
        self.assertIsNotNone(inv.id)
        self.assertEqual(inv.lines.count(), 2)

    def test_create_group_and_bookings_with_advance(self):
        from bookings.services import create_booking_group_and_bookings
        from bookings.models import RentCycle, BookingType

        unit_rows = [{"unit": self.unit1, "rate": self.unit1.daily_price}]
        state = {"start_date": self.start, "end_date": self.end, "adults": 1, "children": 0}

        group, bookings, inv = create_booking_group_and_bookings(
            property_profile=self.prop,
            guest=self.guest,
            unit_rows=unit_rows,
            state=state,
            rent_cycle=RentCycle.NIGHTLY,
            booking_type=BookingType.HOTEL,
            discount=Decimal("5.000"),
            advance=Decimal("10.000"),
            payment_method="cash",
            notes="test",
        )

        self.assertIsNotNone(group.id)
        self.assertEqual(len(bookings), 1)
        self.assertIsNotNone(inv.id)
        # lines: 1 unit + 1 discount
        self.assertEqual(inv.lines.count(), 2)
        self.assertEqual(inv.payments.count(), 1)
