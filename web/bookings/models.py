from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models import TimeStampedModel
from settings_app.models import PropertyProfile
from inventory.models import Unit
from guests.models import Guest


class BookingStatus(models.TextChoices):
    RESERVED = "reserved", "Reserved"
    CHECKED_IN = "checked_in", "Checked-in"
    CHECKED_OUT = "checked_out", "Checked-out"
    CANCELLED = "cancelled", "Cancelled"
    NO_SHOW = "no_show", "No-show"


class BookingType(models.TextChoices):
    HOTEL = "hotel", "Hotel"
    APARTMENT = "apartment", "Apartment"


class RentCycle(models.TextChoices):
    NIGHTLY = "nightly", "Nightly"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"


class BookingGroup(TimeStampedModel):
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="booking_groups")
    guest = models.ForeignKey(Guest, on_delete=models.PROTECT, related_name="booking_groups")

    booking_type = models.CharField(max_length=20, choices=BookingType.choices, default=BookingType.HOTEL)
    rent_cycle = models.CharField(max_length=20, choices=RentCycle.choices, default=RentCycle.NIGHTLY)
    status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.RESERVED)

    start_date = models.DateField()
    end_date = models.DateField()

    adults = models.PositiveIntegerField(default=1)
    children = models.PositiveIntegerField(default=0)

    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property_profile", "status"]),
            models.Index(fields=["property_profile", "start_date", "end_date"]),
        ]

    def __str__(self):
        guest_name = getattr(self.guest, "full_name", str(self.guest_id))
        return f"Group {self.id} - {guest_name} ({self.start_date}→{self.end_date})"


class Booking(TimeStampedModel):
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="bookings")
    guest = models.ForeignKey(Guest, on_delete=models.PROTECT, related_name="bookings")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="bookings")
    booking_group = models.ForeignKey(BookingGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings")

    booking_type = models.CharField(max_length=20, choices=BookingType.choices, default=BookingType.HOTEL)
    rent_cycle = models.CharField(max_length=20, choices=RentCycle.choices, default=RentCycle.NIGHTLY)

    status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.RESERVED)

    start_date = models.DateField()
    end_date = models.DateField()

    adults = models.PositiveIntegerField(default=1)
    children = models.PositiveIntegerField(default=0)

    rate = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal("0.000"))
    discount = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal("0.000"))
    deposit = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal("0.000"))

    # ✅ Price freeze (lock)
    price_locked = models.BooleanField(default=False)
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_rate = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal("0.000"))
    locked_discount = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal("0.000"))
    locked_deposit = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal("0.000"))
    locked_total = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))

    # ✅ Soft archive
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property_profile", "status"]),
            models.Index(fields=["property_profile", "start_date", "end_date"]),
            models.Index(fields=["unit", "start_date", "end_date"]),
            models.Index(fields=["property_profile", "is_archived"]),
        ]

    def __str__(self):
        unit_code = getattr(self.unit, "code", str(self.unit_id))
        guest_name = getattr(self.guest, "full_name", str(self.guest_id))
        return f"{guest_name} - {unit_code} ({self.start_date}→{self.end_date})"

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError("end_date must be after start_date")

        if self.unit_id and self.property_profile_id and self.unit.property_profile_id != self.property_profile_id:
            raise ValidationError("Unit does not belong to the selected property_profile")

        if self.guest_id and self.property_profile_id and self.guest.property_profile_id != self.property_profile_id:
            raise ValidationError("Guest does not belong to the selected property_profile")

        if self.unit_id and self.start_date and self.end_date:
            if not is_unit_available(self.unit_id, self.start_date, self.end_date, exclude_booking_id=self.id):
                raise ValidationError("Unit is not available for the selected dates")

    @property
    def nights(self) -> int:
        return (self.end_date - self.start_date).days

    def estimate_total(self) -> Decimal:
        # ✅ If locked, return locked_total always
        if self.price_locked:
            return self.locked_total if self.locked_total > Decimal("0.000") else Decimal("0.000")

        if self.rent_cycle == RentCycle.MONTHLY:
            base = self.rate
        else:
            base = Decimal(self.nights) * self.rate

        total = base - self.discount
        return total if total > Decimal("0.000") else Decimal("0.000")

    def lock_pricing(self):
        """
        Freeze pricing fields so later rate changes don't affect this booking.
        Call this when booking is confirmed/issued invoice/checked-in.
        """
        total = self.estimate_total()
        self.price_locked = True
        self.locked_at = timezone.now()
        self.locked_rate = self.rate
        self.locked_discount = self.discount
        self.locked_deposit = self.deposit
        self.locked_total = total

    def archive(self):
        self.is_archived = True
        self.archived_at = timezone.now()


def is_unit_available(unit_id: int, start_date: date, end_date: date, exclude_booking_id: int | None = None) -> bool:
    overlaps = Q(start_date__lt=end_date) & Q(end_date__gt=start_date)
    qs = (
        Booking.objects.filter(unit_id=unit_id, is_archived=False)  # ✅ ignore archived
        .exclude(status__in=[BookingStatus.CANCELLED, BookingStatus.NO_SHOW])
        .filter(overlaps)
    )
    if exclude_booking_id:
        qs = qs.exclude(id=exclude_booking_id)
    return not qs.exists()