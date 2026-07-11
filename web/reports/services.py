from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count

from bookings.models import Booking, BookingStatus
from inventory.models import Unit


def _daterange(d1: date, d2: date):
    d = d1
    while d <= d2:
        yield d
        d += timedelta(days=1)


def calc_occupancy(property_profile_id: int, date_from: date, date_to: date) -> dict:
    """
    Occupancy = booked_nights / (active_units * nights)
    We count nights based on bookings overlap.
    """
    if date_to < date_from:
        return {"detail": "Invalid range"}

    units_count = Unit.objects.filter(property_profile_id=property_profile_id, is_active=True).count()
    nights = (date_to - date_from).days + 1
    if units_count <= 0 or nights <= 0:
        return {"units": units_count, "nights": nights, "booked_nights": 0, "occupancy_pct": 0}

    end_exclusive = date_to + timedelta(days=1)
    bookings = Booking.objects.filter(
        property_profile_id=property_profile_id,
        start_date__lt=end_exclusive,
        end_date__gt=date_from,
    ).exclude(status__in=[BookingStatus.CANCELLED, BookingStatus.NO_SHOW])

    booked_nights = 0
    for b in bookings:
        # booking nights are [start_date, end_date)
        overlap_start = max(date_from, b.start_date)
        overlap_end = min(end_exclusive, b.end_date)
        if overlap_end > overlap_start:
            booked_nights += (overlap_end - overlap_start).days

    denom = units_count * nights
    pct = int((booked_nights / denom) * 100) if denom else 0
    return {"units": units_count, "nights": nights, "booked_nights": booked_nights, "occupancy_pct": pct}


def bookings_kpis(property_profile_id: int, date_from: date, date_to: date) -> dict:
    end_exclusive = date_to + timedelta(days=1)
    qs = Booking.objects.filter(
        property_profile_id=property_profile_id,
        start_date__lt=end_exclusive,
        end_date__gt=date_from,
    )
    total = qs.count()
    by_status = {row["status"]: row["c"] for row in qs.values("status").annotate(c=Count("id"))}

    revenue = Decimal("0.000")
    active_qs = qs.exclude(status__in=[BookingStatus.CANCELLED, BookingStatus.NO_SHOW])
    for booking in active_qs:
        if booking.price_locked:
            revenue += booking.locked_total or Decimal("0.000")
        else:
            revenue += booking.estimate_total()

    return {
        "total_bookings": total,
        "by_status": by_status,
        "revenue_estimated": str(revenue),
    }
