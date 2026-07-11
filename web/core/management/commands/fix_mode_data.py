from __future__ import annotations

from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from bookings.models import Booking, BookingType
from guests.models import Guest
from inventory.models import Unit, UnitType
from settings_app.models import BusinessType


class Command(BaseCommand):
    help = "Fix business_type separation for UnitType and Guest using existing data."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Apply changes (default is dry run)")

    def handle(self, *args, **options):
        apply_changes = bool(options.get("apply"))

        hotel_categories = {
            Unit.UnitCategory.SINGLE,
            Unit.UnitCategory.DOUBLE,
            Unit.UnitCategory.TRIPLE,
            Unit.UnitCategory.TWIN,
            Unit.UnitCategory.KING,
            Unit.UnitCategory.QUEEN,
            Unit.UnitCategory.CONNECTING,
            Unit.UnitCategory.STUDIO,
            Unit.UnitCategory.VILLA,
        }
        apartment_categories = {
            Unit.UnitCategory.STUDIO_APT,
            Unit.UnitCategory.ONE_BHK,
            Unit.UnitCategory.TWO_BHK,
            Unit.UnitCategory.THREE_BHK,
            Unit.UnitCategory.FOUR_BHK,
            Unit.UnitCategory.FIVE_BHK,
            Unit.UnitCategory.DUPLEX,
            Unit.UnitCategory.PENTHOUSE,
            Unit.UnitCategory.LOFT,
        }

        unit_type_changes = 0
        guest_changes = 0

        def _infer_unit_type_business_type(unit_type: UnitType):
            units = list(Unit.objects.filter(unit_type=unit_type).only("id", "category"))
            if units:
                has_apartment = any(u.category in apartment_categories for u in units if u.category)
                has_hotel = any(u.category in hotel_categories for u in units if u.category)

                if has_apartment and not has_hotel:
                    return BusinessType.APARTMENTS
                if has_hotel and not has_apartment:
                    return BusinessType.HOTEL

            booking_types = list(
                Booking.objects.filter(unit__unit_type=unit_type).values_list("booking_type", flat=True)
            )
            if booking_types:
                counts = Counter(booking_types)
                winner = BookingType.APARTMENT if counts[BookingType.APARTMENT] > counts[BookingType.HOTEL] else BookingType.HOTEL
                return BusinessType.APARTMENTS if winner == BookingType.APARTMENT else BusinessType.HOTEL

            return None

        def _infer_guest_business_type(guest: Guest):
            last_booking = (
                Booking.objects.filter(guest=guest)
                .order_by("-start_date", "-created_at")
                .only("booking_type")
                .first()
            )
            if not last_booking:
                return None
            return BusinessType.APARTMENTS if last_booking.booking_type == BookingType.APARTMENT else BusinessType.HOTEL

        scope = transaction.atomic() if apply_changes else _nullcontext()
        with scope:
            for unit_type in UnitType.objects.select_related("property_profile").all():
                inferred = _infer_unit_type_business_type(unit_type)
                if inferred and unit_type.business_type != inferred:
                    unit_type_changes += 1
                    self.stdout.write(
                        f"UnitType #{unit_type.id} ({unit_type.name_en}) {unit_type.business_type} -> {inferred}"
                    )
                    if apply_changes:
                        unit_type.business_type = inferred
                        unit_type.save(update_fields=["business_type", "updated_at"])

            for guest in Guest.objects.all().only("id", "business_type"):
                inferred = _infer_guest_business_type(guest)
                if inferred and guest.business_type != inferred:
                    guest_changes += 1
                    self.stdout.write(f"Guest #{guest.id} {guest.business_type} -> {inferred}")
                    if apply_changes:
                        guest.business_type = inferred
                        guest.save(update_fields=["business_type", "updated_at"])

        if apply_changes:
            self.stdout.write(self.style.SUCCESS("Mode data fix applied."))
        else:
            self.stdout.write(self.style.WARNING("Dry run only. Re-run with --apply to save changes."))

        self.stdout.write(f"UnitType changes: {unit_type_changes}")
        self.stdout.write(f"Guest changes: {guest_changes}")


class _nullcontext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False
