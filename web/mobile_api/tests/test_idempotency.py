from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model


class MobileIdempotencyTests(TestCase):
    def setUp(self) -> None:
        from django.apps import apps

        PropertyProfile = apps.get_model("settings_app", "PropertyProfile")
        UnitType = apps.get_model("inventory", "UnitType")
        Unit = apps.get_model("inventory", "Unit")
        MobileCustomer = apps.get_model("mobile_api", "MobileCustomer")

        User = get_user_model()
        self.user = User.objects.create_user(username="muser", password="pass")
        self.customer = MobileCustomer.objects.create(user=self.user, full_name="M Test")

        self.prop = PropertyProfile.objects.create(name_en="Idemp Prop")
        self.unit_type = UnitType.objects.create(property_profile=self.prop, business_type=self.prop.business_type, name_en="Std", base_rate=Decimal("10.000"))
        self.unit = Unit.objects.create(property_profile=self.prop, unit_type=self.unit_type, code="R1", daily_price=Decimal("20.000"), monthly_price=Decimal("400.000"))

        self.check_in = date.today()
        self.check_out = self.check_in + timedelta(days=2)

    def test_booking_idempotency_returns_same_booking(self):
        from mobile_api.bookings.services import create_mobile_booking

        booking_a, _ = create_mobile_booking(
            customer=self.customer,
            unit=self.unit,
            check_in=self.check_in,
            check_out=self.check_out,
            guest_count=1,
            idempotency_key="key-123",
        )

        booking_b, _ = create_mobile_booking(
            customer=self.customer,
            unit=self.unit,
            check_in=self.check_in,
            check_out=self.check_out,
            guest_count=1,
            idempotency_key="key-123",
        )

        self.assertEqual(booking_a.id, booking_b.id)

    def test_payment_idempotency_returns_same_payment(self):
        from mobile_api.bookings.services import create_mobile_booking, create_payment_intent_placeholder

        booking, quote = create_mobile_booking(
            customer=self.customer,
            unit=self.unit,
            check_in=self.check_in,
            check_out=self.check_out,
            guest_count=1,
        )

        p1 = create_payment_intent_placeholder(
            customer=self.customer,
            booking_id=booking.id,
            amount=quote.total,
            currency=quote.currency,
            idempotency_key="pay-key-abc",
        )

        p2 = create_payment_intent_placeholder(
            customer=self.customer,
            booking_id=booking.id,
            amount=quote.total,
            currency=quote.currency,
            idempotency_key="pay-key-abc",
        )

        self.assertEqual(p1.id, p2.id)
