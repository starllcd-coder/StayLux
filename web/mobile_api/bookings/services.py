from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db import IntegrityError
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from bookings.models import Booking, BookingStatus, is_unit_available
from inventory.models import Unit
from mobile_api.auth.models import MobileCustomer
from mobile_api.bookings.models import (
    MobileIdempotencyKey,
    MobilePaymentRecord,
    MobilePaymentSecurityCheck,
)
from mobile_api.discovery.services import StayDateRange, get_effective_unit_prices
from notifications.models import Channel, OutboxMessage


@dataclass
class BookingQuote:
    unit: Unit
    check_in: date
    check_out: date
    guest_count: int
    nights: int
    currency: str
    booking_type: str
    rent_cycle: str
    nightly_price: Decimal
    monthly_price: Decimal
    subtotal: Decimal
    discount_amount: Decimal
    discount_label: str
    coupon_code: str
    taxes: Decimal
    fees: Decimal
    total: Decimal


def validate_booking_dates(check_in: date, check_out: date):
    if check_out <= check_in:
        raise ValidationError({"dates": "Check-out must be after check-in."})


def validate_guest_count(guest_count: int):
    if guest_count <= 0:
        raise ValidationError({"guest_count": "Guest count must be greater than zero."})


def validate_unit_for_booking(unit: Unit, guest_count: int):
    if not unit.is_active:
        raise ValidationError({"unit_id": "Selected unit is inactive."})

    if guest_count > unit.guest_capacity:
        raise ValidationError({"guest_count": "Guest count exceeds unit capacity."})


def validate_unit_availability(unit: Unit, check_in: date, check_out: date):
    if not is_unit_available(unit.id, check_in, check_out):
        raise ValidationError({"unit_id": "Unit is not available for the selected dates."})


def calculate_booking_quote(
    unit: Unit,
    check_in: date,
    check_out: date,
    guest_count: int,
    coupon_code: str = "",
) -> BookingQuote:
    validate_booking_dates(check_in, check_out)
    validate_guest_count(guest_count)
    validate_unit_for_booking(unit, guest_count)
    validate_unit_availability(unit, check_in, check_out)

    stay_range = StayDateRange(check_in=check_in, check_out=check_out)
    price_data = get_effective_unit_prices(unit, stay_range)

    nights = max((check_out - check_in).days, 0)
    subtotal = price_data["estimated_total"] or Decimal("0.000")

    normalized_coupon = (coupon_code or "").strip().upper()
    coupon_map = {
        "WELCOME10": Decimal("0.10"),
        "FAMILY5": Decimal("0.05"),
        "LUXE15": Decimal("0.15"),
    }
    discount_rate = coupon_map.get(normalized_coupon, Decimal("0.00"))
    discount_amount = (subtotal * discount_rate).quantize(Decimal("0.001"))
    discounted_subtotal = max(subtotal - discount_amount, Decimal("0.000"))

    taxes = Decimal("0.000")
    fees = Decimal("0.000")
    total = discounted_subtotal + taxes + fees

    return BookingQuote(
        unit=unit,
        check_in=check_in,
        check_out=check_out,
        guest_count=guest_count,
        nights=nights,
        currency=unit.property_profile.currency,
        booking_type=price_data["booking_type"],
        rent_cycle=price_data["rent_cycle"],
        nightly_price=price_data["nightly_price"],
        monthly_price=price_data["monthly_price"],
        subtotal=subtotal,
        discount_amount=discount_amount,
        discount_label=(f"{int(discount_rate * 100)}% off" if discount_rate > 0 else ""),
        coupon_code=normalized_coupon,
        taxes=taxes,
        fees=fees,
        total=total,
    )


def _resolve_booking_status() -> str:
    # Match bookings.BookingStatus choices in this project.
    return BookingStatus.RESERVED if hasattr(BookingStatus, "RESERVED") else "reserved"


def get_customer_guest_ids(customer: MobileCustomer) -> list[int]:
    """
    Resolve guest records linked to a mobile customer using stable identity data.
    We prefer exact email/mobile matches across properties.
    """
    from guests.models import Guest

    email = (getattr(customer, "email", "") or "").strip().lower()
    mobile = (getattr(customer, "mobile", "") or "").strip()

    filters = Q()
    if email:
        filters |= Q(email__iexact=email)
    if mobile:
        filters |= Q(phone=mobile) | Q(whatsapp=mobile)

    if not filters:
        return []

    return list(Guest.objects.filter(filters).values_list("id", flat=True))


def get_customer_booking_ids(customer: MobileCustomer) -> list[int]:
    """
    Resolve booking ids directly linked to the customer by mobile-side records.
    This keeps booking history visible even if traveler email/phone differs
    from the account email/phone used in `get_customer_guest_ids`.
    """
    booking_ids = set(
        MobilePaymentRecord.objects.filter(customer=customer, booking_id__isnull=False)
        .values_list("booking_id", flat=True)
    )
    booking_ids.update(
        MobileIdempotencyKey.objects.filter(customer=customer, booking_id__isnull=False)
        .values_list("booking_id", flat=True)
    )
    return [bid for bid in booking_ids if bid]


def _notify_property_booking_event(
    *,
    booking: Booking,
    event_key: str,
    title: str,
    details: str,
) -> None:
    """
    Create an in-app outbox message so web users see mobile booking events
    in the notification bell/center even when WhatsApp sending is disabled.
    """
    prop = booking.property_profile
    to_phone = (getattr(prop, "whatsapp", "") or getattr(prop, "phone", "") or "").strip()
    content = (
        f"{title}\n"
        f"Booking #{booking.id} · Unit {getattr(booking.unit, 'code', '-')}\n"
        f"{booking.start_date} -> {booking.end_date}\n"
        f"{details}"
    )
    OutboxMessage.objects.create(
        property_profile=prop,
        channel=Channel.WHATSAPP,
        to_phone=to_phone,
        event_key=event_key,
        language="en",
        content=content,
    )


@transaction.atomic
def create_mobile_booking(
    *,
    customer: MobileCustomer,
    unit: Unit,
    check_in: date,
    check_out: date,
    guest_count: int,
    traveler_name: str = "",
    traveler_email: str = "",
    traveler_phone: str = "",
    notes: str = "",
    idempotency_key: str | None = None,
    coupon_code: str = "",
):
    # Idempotency by explicit key: if provided, return any linked booking without
    # re-running availability checks (which may fail because an existing booking exists).
    from mobile_api.bookings.models import MobileIdempotencyKey

    if idempotency_key:
        existing_key = MobileIdempotencyKey.objects.filter(key=idempotency_key).first()
        if existing_key and existing_key.booking_id:
            existing = Booking.objects.filter(id=existing_key.booking_id).first()
            if existing:
                # Build a lightweight quote from the existing booking to return alongside it.
                est_total = getattr(existing, "locked_total", None) or getattr(existing, "estimate_total", lambda: 0)()
                quote = BookingQuote(
                    unit=existing.unit,
                    check_in=existing.start_date,
                    check_out=existing.end_date,
                    guest_count=getattr(existing, "adults", 1),
                    nights=getattr(existing, "nights", (existing.end_date - existing.start_date).days),
                    currency=existing.unit.property_profile.currency,
                    booking_type=getattr(existing, "booking_type", ""),
                    rent_cycle=getattr(existing, "rent_cycle", ""),
                    nightly_price=Decimal("0.000"),
                    monthly_price=Decimal("0.000"),
                    subtotal=Decimal(est_total),
                    discount_amount=Decimal("0.000"),
                    discount_label="",
                    coupon_code=(coupon_code or "").strip().upper(),
                    taxes=Decimal("0.000"),
                    fees=Decimal("0.000"),
                    total=Decimal(est_total),
                )
                return existing, quote

    # No explicit idempotency hit — calculate quote (performs availability checks).
    quote = calculate_booking_quote(unit, check_in, check_out, guest_count, coupon_code=coupon_code)

    # (Fallback idempotency moved to after we ensure/create a Guest record.)

    booking_payload = {
        "unit": unit,
        # Booking.guest references a `Guest` model (not the auth user). Ensure a Guest exists.
        "guest": None,
        "property_profile": unit.property_profile,
        "start_date": check_in,
        "end_date": check_out,
        "adults": guest_count,
        "children": 0,
    }

    booking_field_names = {field.name for field in Booking._meta.fields}

    if "status" in booking_field_names:
        booking_payload["status"] = _resolve_booking_status()
    if "booking_type" in booking_field_names:
        booking_payload["booking_type"] = quote.booking_type
    if "rent_cycle" in booking_field_names:
        booking_payload["rent_cycle"] = quote.rent_cycle
    if "locked_total" in booking_field_names:
        booking_payload["locked_total"] = quote.total
    if "rate" in booking_field_names:
        booking_payload["rate"] = (
            quote.monthly_price if quote.rent_cycle == "monthly" else quote.nightly_price
        )
    if "discount" in booking_field_names:
        booking_payload["discount"] = quote.discount_amount
    if "deposit" in booking_field_names:
        booking_payload["deposit"] = Decimal("0.000")
    if "price_locked" in booking_field_names:
        booking_payload["price_locked"] = True
    if "locked_rate" in booking_field_names:
        booking_payload["locked_rate"] = (
            quote.monthly_price if quote.rent_cycle == "monthly" else quote.nightly_price
        )
    if "locked_discount" in booking_field_names:
        booking_payload["locked_discount"] = quote.discount_amount
    if "locked_deposit" in booking_field_names:
        booking_payload["locked_deposit"] = Decimal("0.000")
    if "locked_at" in booking_field_names:
        booking_payload["locked_at"] = timezone.now()
    if "notes" in booking_field_names:
        booking_payload["notes"] = notes
    # Some projects include guest contact fields; only set if present.
    if "guest_name" in booking_field_names:
        booking_payload["guest_name"] = traveler_name or getattr(customer, "full_name", "")
    if "guest_email" in booking_field_names:
        booking_payload["guest_email"] = traveler_email or getattr(customer, "email", "")
    if "guest_phone" in booking_field_names:
        booking_payload["guest_phone"] = traveler_phone or getattr(customer, "mobile", "")

    # Ensure a Guest record exists for this mobile customer within the unit's property.
    try:
        from guests.models import Guest

        full_name = (traveler_name or getattr(customer, "full_name", "") or "").strip()
        phone = (traveler_phone or getattr(customer, "mobile", "") or "").strip()
        email = (traveler_email or getattr(customer, "email", "") or "").strip().lower()

        guest_obj = None
        base_qs = Guest.objects.filter(property_profile=unit.property_profile)
        if email:
            guest_obj = base_qs.filter(email__iexact=email).first()
        if guest_obj is None and phone:
            guest_obj = base_qs.filter(Q(phone=phone) | Q(whatsapp=phone)).first()
        if guest_obj is None and full_name:
            guest_obj = base_qs.filter(full_name=full_name).first()

        if guest_obj is None:
            guest_obj = Guest.objects.create(
                property_profile=unit.property_profile,
                business_type=getattr(unit.property_profile, "business_type", "hotel"),
                full_name=full_name or "Mobile Guest",
                phone=phone,
                whatsapp=phone,
                email=email,
            )
        else:
            changed_fields = []
            if full_name and guest_obj.full_name != full_name:
                guest_obj.full_name = full_name
                changed_fields.append("full_name")
            if phone and guest_obj.phone != phone:
                guest_obj.phone = phone
                changed_fields.append("phone")
            if phone and guest_obj.whatsapp != phone:
                guest_obj.whatsapp = phone
                changed_fields.append("whatsapp")
            if email and guest_obj.email.lower() != email:
                guest_obj.email = email
                changed_fields.append("email")
            if changed_fields:
                changed_fields.append("updated_at")
                guest_obj.save(update_fields=changed_fields)

        booking_payload["guest"] = guest_obj
    except Exception as exc:
        raise ValidationError(
            {"traveler": f"Could not prepare traveler profile for booking. ({exc})"}
        )

    if booking_payload.get("guest") is None:
        raise ValidationError(
            {"traveler": "Traveler profile is required to complete booking."}
        )

    # After establishing a Guest instance, perform fallback duplicate booking check.
    existing = Booking.objects.filter(
        guest=booking_payload.get("guest"),
        unit=unit,
        start_date=check_in,
        end_date=check_out,
    ).first()
    if existing:
        return existing, quote

    try:
        booking = Booking.objects.create(**booking_payload)
    except IntegrityError as exc:
        raise ValidationError({"booking": f"Could not create booking record. ({exc})"})
    # Loyalty: award lightweight points for completed booking creation flow.
    try:
        points = int((quote.total or Decimal("0.000")) // Decimal("10.000"))
    except (ArithmeticError, TypeError, ValueError):
        points = 1
    try:
        customer.add_loyalty_points(max(points, 1))
    except Exception as exc:
        raise ValidationError({"booking": f"Booking created but loyalty update failed. ({exc})"})

    # Persist idempotency mapping if a key was provided
    if idempotency_key:
        MobileIdempotencyKey.objects.get_or_create(
            key=idempotency_key,
            defaults={"customer": customer, "booking_id": booking.id},
        )

    _notify_property_booking_event(
        booking=booking,
        event_key="mobile_booking_created",
        title="New mobile booking created",
        details=(
            f"Guest: {booking.guest.full_name or 'Mobile Guest'} · "
            f"Amount: {quote.currency} {quote.total}"
        ),
    )

    return booking, quote


def create_payment_intent_placeholder(
    *,
    customer: MobileCustomer,
    booking_id: int | None,
    amount: Decimal,
    currency: str,
    payment_method: str = "",
    provider: str = "",
    idempotency_key: str | None = None,
):
    # If explicit idempotency key provided, try to return linked payment
    from mobile_api.bookings.models import MobileIdempotencyKey

    if idempotency_key:
        existing_key = MobileIdempotencyKey.objects.filter(key=idempotency_key).first()
        if existing_key and existing_key.payment_id:
            existing_payment = MobilePaymentRecord.objects.filter(id=existing_key.payment_id).first()
            if existing_payment and existing_payment.status == MobilePaymentRecord.PaymentStatus.PENDING:
                return existing_payment

    # Avoid duplicate payment records for the same booking and amount (fallback idempotency)
    if booking_id:
        existing = MobilePaymentRecord.objects.filter(
            customer=customer,
            booking_id=booking_id,
            amount=amount,
            currency=currency,
        ).order_by("-created_at").first()
        if existing and existing.status == MobilePaymentRecord.PaymentStatus.PENDING:
            return existing

    reference = f"stlx-{customer.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"

    payment = MobilePaymentRecord.objects.create(
        customer=customer,
        booking_id=booking_id,
        provider=provider or "pending_provider",
        provider_reference=reference,
        currency=currency,
        amount=amount,
        status=MobilePaymentRecord.PaymentStatus.PENDING,
        payment_method=payment_method,
        client_secret="pending_provider_integration",
    )
    MobilePaymentSecurityCheck.objects.get_or_create(payment=payment)

    # Save idempotency mapping if key provided
    if idempotency_key:
        MobileIdempotencyKey.objects.get_or_create(
            key=idempotency_key,
            defaults={"customer": customer, "payment_id": payment.id},
        )
    return payment


def run_payment_security_check(*, payment: MobilePaymentRecord, otp_code: str = "", billing_country: str = ""):
    check, _ = MobilePaymentSecurityCheck.objects.get_or_create(payment=payment)

    flags = []
    risk_score = 10

    if payment.amount and payment.amount >= Decimal("500.000"):
        risk_score += 35
        flags.append("high_amount")
    if payment.provider_reference and "test" in payment.provider_reference.lower():
        risk_score += 10
        flags.append("test_reference")
    if billing_country and billing_country.upper() not in {"OM", "AE", "SA", "QA", "BH", "KW"}:
        risk_score += 25
        flags.append("cross_region")
    if otp_code and len(otp_code.strip()) < 4:
        risk_score += 20
        flags.append("weak_otp")

    requires_review = risk_score >= 60
    if requires_review:
        check.verification_status = MobilePaymentSecurityCheck.VerificationStatus.REVIEW
        payment.status = MobilePaymentRecord.PaymentStatus.REQUIRES_ACTION
    else:
        check.verification_status = MobilePaymentSecurityCheck.VerificationStatus.VERIFIED
        payment.status = MobilePaymentRecord.PaymentStatus.PAID

    check.risk_score = max(0, min(100, risk_score))
    check.requires_manual_review = requires_review
    check.fraud_flags = flags
    check.verification_notes = "Automated risk scoring completed."
    check.save(
        update_fields=[
            "verification_status",
            "risk_score",
            "requires_manual_review",
            "fraud_flags",
            "verification_notes",
            "updated_at",
        ]
    )
    payment.save(update_fields=["status", "updated_at"])
    return check


def cancel_customer_booking(*, booking: Booking):
    if hasattr(BookingStatus, "CANCELLED"):
        booking.status = BookingStatus.CANCELLED
    else:
        booking.status = "cancelled"
    booking.save(update_fields=["status"])
    _notify_property_booking_event(
        booking=booking,
        event_key="mobile_booking_cancelled",
        title="Mobile booking cancelled by customer",
        details=f"Guest: {booking.guest.full_name or 'Mobile Guest'}",
    )
    return booking
