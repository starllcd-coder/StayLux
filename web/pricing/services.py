from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from inventory.models import Unit
from .models import RatePlan, SeasonalRateRule, RatePlanScope


@dataclass
class EffectivePrice:
    currency: str
    nightly: Decimal
    monthly: Decimal
    source: str  # "unit_override" | "seasonal_rule" | "rate_plan" | "unit_type_base"


def _parse_weekdays(s: str) -> set[int]:
    s = (s or "").strip()
    if not s:
        return set()
    out = set()
    for p in s.split(","):
        p = p.strip()
        if not p:
            continue
        out.add(int(p))
    return out


def get_applicable_rate_plan(unit: Unit) -> RatePlan | None:
    # Prefer unit-specific plan, then unit_type plan
    rp = (
        RatePlan.objects.filter(property_profile=unit.property_profile, is_active=True, scope=RatePlanScope.UNIT, unit=unit)
        .order_by("-created_at")
        .first()
    )
    if rp:
        return rp
    return (
        RatePlan.objects.filter(property_profile=unit.property_profile, is_active=True, scope=RatePlanScope.UNIT_TYPE, unit_type=unit.unit_type)
        .order_by("-created_at")
        .first()
    )


def get_effective_price_for_date(unit: Unit, d: date) -> EffectivePrice:
    # 1) unit overrides
    # NOTE:
    # This codebase's Unit/UnitType currently does NOT define "base_price_nightly/base_price_monthly"
    # fields (it has UnitType.base_rate). Some earlier iterations referenced those names.
    # We keep optional override support (if you later add those fields), but must be safe today.
    nightly_override = getattr(unit, "price_override_nightly", None)
    monthly_override = getattr(unit, "price_override_monthly", None)
    if nightly_override is not None or monthly_override is not None:
        base_nightly = getattr(unit.unit_type, "base_price_nightly", None)
        base_monthly = getattr(unit.unit_type, "base_price_monthly", None)

        # Fallback to UnitType.base_rate when nightly/monthly bases aren't defined.
        if base_nightly is None:
            base_nightly = getattr(unit.unit_type, "base_rate", Decimal("0.000"))
        if base_monthly is None:
            # heuristic monthly fallback: 30 nights
            base_monthly = (base_nightly or Decimal("0.000")) * Decimal("30")

        nightly = nightly_override if nightly_override is not None else base_nightly
        monthly = monthly_override if monthly_override is not None else base_monthly
        return EffectivePrice(currency="OMR", nightly=nightly, monthly=monthly, source="unit_override")

    # 2) rate plan + seasonal rules
    rp = get_applicable_rate_plan(unit)
    if rp:
        weekday = d.weekday()
        rules = (
            SeasonalRateRule.objects.filter(
                property_profile=unit.property_profile,
                is_active=True,
                rate_plan=rp,
                date_from__lte=d,
                date_to__gte=d,
            )
            .order_by("-priority", "-created_at")
        )
        for r in rules:
            wset = _parse_weekdays(r.weekdays)
            if wset and weekday not in wset:
                continue
            nightly = r.price_nightly if r.price_nightly is not None else rp.base_price_nightly
            monthly = r.price_monthly if r.price_monthly is not None else rp.base_price_monthly
            return EffectivePrice(currency=rp.currency, nightly=nightly, monthly=monthly, source="seasonal_rule")

        return EffectivePrice(currency=rp.currency, nightly=rp.base_price_nightly, monthly=rp.base_price_monthly, source="rate_plan")

    # 3) fallback to unit_type base
    base_nightly = getattr(unit.unit_type, "base_price_nightly", None)
    base_monthly = getattr(unit.unit_type, "base_price_monthly", None)
    if base_nightly is None:
        base_nightly = getattr(unit.unit_type, "base_rate", Decimal("0.000"))
    if base_monthly is None:
        base_monthly = (base_nightly or Decimal("0.000")) * Decimal("30")
    return EffectivePrice(currency="OMR", nightly=base_nightly, monthly=base_monthly, source="unit_type_base")


def compute_booking_total(unit: Unit, check_in: date, check_out: date) -> tuple[Decimal, str]:
    """
    Hotel-style: sum nightly for each night (check_out is exclusive).
    """
    if check_out <= check_in:
        return Decimal("0.000"), "OMR"

    total = Decimal("0.000")
    cur = "OMR"
    d = check_in
    while d < check_out:
        p = get_effective_price_for_date(unit, d)
        cur = p.currency
        total += (p.nightly or Decimal("0.000"))
        d += timedelta(days=1)

    return total.quantize(Decimal("0.001")), cur