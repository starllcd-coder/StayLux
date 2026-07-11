from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client
from django.test import TestCase
from django.urls import resolve

from bookings.models import Booking
from guests.models import Guest
from inventory.models import Unit, UnitType
from mobile_api.auth.models import MobileCustomer
from mobile_api.bookings.serializers import BookingSerializer
from mobile_api.bookings.services import get_customer_guest_ids
from settings_app.models import PropertyProfile


class MobileApiAlignmentTests(TestCase):
    def setUp(self) -> None:
        User = get_user_model()
        self.client = Client()
        self.user = User.objects.create_user(
            username="mcustomer",
            email="mobile@example.com",
            password="pass1234",
        )
        self.customer = MobileCustomer.objects.create(
            user=self.user,
            full_name="Mobile Customer",
            mobile="90000000",
        )
        self.property = PropertyProfile.objects.create(name_en="Test Property")
        self.unit_type = UnitType.objects.create(
            property_profile=self.property,
            business_type=self.property.business_type,
            name_en="Standard",
            base_rate=Decimal("10.000"),
        )
        self.unit = Unit.objects.create(
            property_profile=self.property,
            unit_type=self.unit_type,
            code="A-1",
            daily_price=Decimal("20.000"),
            monthly_price=Decimal("300.000"),
        )

    def test_get_customer_guest_ids_matches_email_or_mobile(self):
        guest = Guest.objects.create(
            property_profile=self.property,
            business_type=self.property.business_type,
            full_name="Mobile Customer",
            email="mobile@example.com",
            phone="90000000",
            whatsapp="90000000",
        )

        guest_ids = get_customer_guest_ids(self.customer)

        self.assertIn(guest.id, guest_ids)

    def test_booking_serializer_maps_start_end_and_guest_count(self):
        guest = Guest.objects.create(
            property_profile=self.property,
            business_type=self.property.business_type,
            full_name="Booking Guest",
            email="mobile@example.com",
            phone="90000000",
        )
        booking = Booking.objects.create(
            property_profile=self.property,
            guest=guest,
            unit=self.unit,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 4),
            adults=2,
            children=1,
        )

        data = BookingSerializer(booking).data

        self.assertEqual(str(data["check_in"]), "2026-02-01")
        self.assertEqual(str(data["check_out"]), "2026-02-04")
        self.assertEqual(data["guest_count"], 3)

    def test_reviews_and_wishlist_are_routed_under_mobile_api(self):
        reviews_match = resolve("/api/mobile/reviews/create/")
        wishlist_match = resolve("/api/mobile/wishlist/toggle/")
        self.assertEqual(reviews_match.func.view_class.__name__, "PropertyReviewCreateView")
        self.assertEqual(wishlist_match.func.view_class.__name__, "WishlistToggleView")

    def test_notifications_list_endpoint_is_available_for_mobile_customer(self):
        self.client.force_login(self.user)
        response = self.client.get("/api/mobile/notifications/")
        self.assertEqual(response.status_code, 200)
