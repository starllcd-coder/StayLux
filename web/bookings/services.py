from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from bookings.models import Booking, BookingGroup, BookingStatus, RentCycle
from billing.models import Invoice, InvoiceLine, InvoiceStatus, Payment, PaymentDirection


def auto_fill_rate_if_missing(booking: Booking) -> list:
    """Ensure a booking has a sensible `rate` (and related fields) when missing.

    Returns a list of updated field names to be saved by the caller.
    """
    updated = []
    try:
        from inventory.models import Unit
    except Exception:
        Unit = None

    if not booking.rate or booking.rate <= Decimal("0.000"):
        unit = getattr(booking, "unit", None)
        rate = Decimal("0.000")
        if unit is not None:
            if booking.rent_cycle == RentCycle.MONTHLY:
                rate = getattr(unit, "monthly_price", None) or getattr(unit, "daily_price", Decimal("0.000"))
            else:
                rate = getattr(unit, "daily_price", Decimal("0.000"))

        booking.rate = (rate or Decimal("0.000")).quantize(Decimal("0.001"))
        updated.append("rate")

    # Leave discount/deposit defaults as-is unless business rules require auto-fill
    return updated


@transaction.atomic
def create_booking_group_and_bookings(*, property_profile, guest, unit_rows: Iterable[dict], state: dict, rent_cycle: str, booking_type: str, discount: Decimal, advance: Decimal, payment_method: str = "cash", notes: str = ""):
    """Create BookingGroup, Bookings for each unit row, Invoice, and optional Payment.

    unit_rows: iterable of dicts with keys: unit, rate, total
    state: dict containing adults/children
    Returns (group, bookings_list, invoice)
    """
    from inventory.models import UnitStatus

    prop = property_profile
    check_in = state.get("start_date")
    check_out = state.get("end_date")

    group = BookingGroup.objects.create(
        property_profile=prop,
        guest=guest,
        booking_type=booking_type,
        rent_cycle=rent_cycle,
        status=BookingStatus.RESERVED,
        start_date=check_in,
        end_date=check_out,
        adults=int(state.get("adults") or 1),
        children=int(state.get("children") or 0),
        notes=notes,
    )

    booking_ids = []
    created_bookings = []
    nights = (check_out - check_in).days

    for row in unit_rows:
        unit = row["unit"]
        rate = (row.get("rate") or Decimal("0.000")).quantize(Decimal("0.001"))
        booking = Booking(
            property_profile=prop,
            guest=guest,
            unit=unit,
            booking_group=group,
            booking_type=booking_type,
            rent_cycle=rent_cycle,
            status=BookingStatus.RESERVED,
            start_date=check_in,
            end_date=check_out,
            adults=int(state.get("adults") or 1),
            children=int(state.get("children") or 0),
            rate=rate,
            discount=Decimal("0.000"),
            deposit=Decimal("0.000"),
            notes=notes,
        )
        booking.full_clean()
        booking.save()
        booking_ids.append(booking.id)
        created_bookings.append(booking)

        # Keep transaction integrity: never swallow errors inside atomic.
        unit.status = UnitStatus.OCCUPIED
        unit.save(update_fields=["status", "updated_at"])

        booking.lock_pricing()
        booking.save(
            update_fields=[
                "price_locked",
                "locked_at",
                "locked_rate",
                "locked_discount",
                "locked_deposit",
                "locked_total",
                "updated_at",
            ]
        )

    # Create invoice for the group
    currency = getattr(prop, "currency", "OMR") or "OMR"
    inv = Invoice(
        property_profile=prop,
        booking=Booking.objects.filter(id=booking_ids[0]).first() if len(booking_ids) == 1 else None,
        booking_group=group,
        guest=guest,
        status=InvoiceStatus.ISSUED,
        issue_date=timezone.localdate(),
        due_date=timezone.localdate(),
        currency=currency,
        notes=notes,
    )
    inv.full_clean()
    inv.save()

    for row in unit_rows:
        unit = row["unit"]
        rate = (row.get("rate") or Decimal("0.000")).quantize(Decimal("0.001"))
        qty = Decimal(nights).quantize(Decimal("0.001")) if rent_cycle != RentCycle.MONTHLY else Decimal("1.000")
        InvoiceLine.objects.create(
            invoice=inv,
            description=f"Accommodation ({getattr(unit, 'code', unit.id)})",
            quantity=qty,
            unit_price=rate,
            discount_amount=Decimal("0.000"),
            tax_rate=Decimal("0.000"),
            tax_amount=Decimal("0.000"),
        )

    if discount and discount > Decimal("0.000"):
        InvoiceLine.objects.create(
            invoice=inv,
            description="Discount",
            quantity=Decimal("1.000"),
            unit_price=Decimal("0.000"),
            discount_amount=discount.quantize(Decimal("0.001")),
            tax_rate=Decimal("0.000"),
            tax_amount=Decimal("0.000"),
        )

    if advance and advance > Decimal("0.000"):
        Payment.objects.create(
            invoice=inv,
            property_profile=prop,
            method=payment_method,
            direction=PaymentDirection.IN,
            amount=advance.quantize(Decimal("0.001")),
            reference="",
            paid_at=timezone.now(),
            notes=notes,
        )

    inv.recalc_and_save()

    return group, created_bookings, inv
