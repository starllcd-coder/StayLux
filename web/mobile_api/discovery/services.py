from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from django.db.models import Avg, Count, Max, Min, Q

from bookings.models import BookingType, RentCycle, is_unit_available
from inventory.models import Unit, UnitStatus
from pricing.models import RatePlan, RatePlanScope, SeasonalRateRule
from settings_app.models import PropertyProfile


@dataclass
class StayDateRange:
    check_in: Optional[date] = None
    check_out: Optional[date] = None

    @property
    def nights(self) -> int:
        if not self.check_in or not self.check_out:
            return 0
        return max((self.check_out - self.check_in).days, 0)


def parse_iso_date(value: str | None) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_guest_count(value) -> Optional[int]:
    if value in (None, "", "null"):
        return None
    try:
        count = int(value)
        return count if count > 0 else None
    except (TypeError, ValueError):
        return None


def parse_decimal(value) -> Optional[float]:
    if value in (None, "", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_stay_range_from_request(request) -> StayDateRange:
    return StayDateRange(
        check_in=parse_iso_date(request.query_params.get("check_in")),
        check_out=parse_iso_date(request.query_params.get("check_out")),
    )


def validate_stay_range(stay_range: StayDateRange) -> None:
    if stay_range.check_in and stay_range.check_out and stay_range.check_out <= stay_range.check_in:
        raise ValueError("check_out must be after check_in.")


def get_base_property_queryset():
    return (
        PropertyProfile.objects.filter(is_active=True)
        .prefetch_related("amenities", "unit_types", "units")
        .annotate(
            min_daily_price=Min("units__daily_price", filter=Q(units__is_active=True)),
            max_daily_price=Max("units__daily_price", filter=Q(units__is_active=True)),
            active_unit_count=Count("units", filter=Q(units__is_active=True), distinct=True),
            average_rating=Avg("reviews__rating", filter=Q(reviews__is_visible=True)),
            total_reviews=Count("reviews", filter=Q(reviews__is_visible=True), distinct=True),
        )
        .order_by("-created_at")
    )


def get_units_for_property(property_obj: PropertyProfile):
    return (
        Unit.objects.filter(property_profile=property_obj, is_active=True)
        .select_related("unit_type", "property_profile")
        .prefetch_related("amenities")
        .order_by("daily_price", "code")
    )


def get_available_units_for_property(
    property_obj: PropertyProfile,
    *,
    check_in: Optional[date] = None,
    check_out: Optional[date] = None,
    guests: Optional[int] = None,
):
    qs = get_units_for_property(property_obj).filter(status=UnitStatus.AVAILABLE)

    if guests:
        qs = qs.filter(guest_capacity__gte=guests)

    if not check_in or not check_out:
        return qs

    available_ids = []
    for unit in qs:
        if is_unit_available(unit.id, check_in, check_out):
            available_ids.append(unit.id)

    return qs.filter(id__in=available_ids)


def choose_rent_cycle(stay_range: StayDateRange) -> str:
    if stay_range.nights >= 28:
        return RentCycle.MONTHLY
    return RentCycle.NIGHTLY


def map_unit_to_booking_type(unit: Unit) -> str:
    business_type = getattr(unit.unit_type, "business_type", "") or getattr(unit.property_profile, "business_type", "")
    if business_type == "apartments":
        return BookingType.APARTMENT
    return BookingType.HOTEL


def _get_rate_plan_for_unit(unit: Unit) -> Optional[RatePlan]:
    plan = (
        RatePlan.objects.filter(
            property_profile=unit.property_profile,
            scope=RatePlanScope.UNIT,
            unit=unit,
            is_active=True,
        )
        .order_by("-created_at")
        .first()
    )
    if plan:
        return plan

    return (
        RatePlan.objects.filter(
            property_profile=unit.property_profile,
            scope=RatePlanScope.UNIT_TYPE,
            unit_type=unit.unit_type,
            is_active=True,
        )
        .order_by("-created_at")
        .first()
    )


def _apply_seasonal_override(
    *,
    plan: Optional[RatePlan],
    stay_range: StayDateRange,
    default_nightly: Decimal,
    default_monthly: Decimal,
) -> tuple[Decimal, Decimal]:
    if not plan or not stay_range.check_in:
        return default_nightly, default_monthly

    rule = (
        SeasonalRateRule.objects.filter(
            property_profile=plan.property_profile,
            rate_plan=plan,
            is_active=True,
            date_from__lte=stay_range.check_in,
            date_to__gte=stay_range.check_in,
        )
        .order_by("-priority", "-created_at")
        .first()
    )

    nightly = default_nightly
    monthly = default_monthly

    if rule:
        if rule.price_nightly is not None:
            nightly = rule.price_nightly
        if rule.price_monthly is not None:
            monthly = rule.price_monthly

    return nightly, monthly


def get_effective_unit_prices(unit: Unit, stay_range: StayDateRange) -> dict:
    unit_daily = unit.daily_price or Decimal("0.000")
    unit_monthly = unit.monthly_price or Decimal("0.000")

    plan = _get_rate_plan_for_unit(unit)

    nightly = unit_daily
    monthly = unit_monthly

    if plan:
        if plan.base_price_nightly is not None and plan.base_price_nightly > 0:
            nightly = plan.base_price_nightly
        if plan.base_price_monthly is not None and plan.base_price_monthly > 0:
            monthly = plan.base_price_monthly

    nightly, monthly = _apply_seasonal_override(
        plan=plan,
        stay_range=stay_range,
        default_nightly=nightly,
        default_monthly=monthly,
    )

    rent_cycle = choose_rent_cycle(stay_range)
    estimated_total = Decimal("0.000")

    if stay_range.check_in and stay_range.check_out:
        if rent_cycle == RentCycle.MONTHLY:
            estimated_total = monthly
        else:
            estimated_total = nightly * Decimal(stay_range.nights or 1)

    return {
        "booking_type": map_unit_to_booking_type(unit),
        "rent_cycle": rent_cycle,
        "nightly_price": nightly,
        "monthly_price": monthly,
        "estimated_total": estimated_total,
    }


def get_property_price_summary(property_obj: PropertyProfile, stay_range: StayDateRange) -> dict:
    units = list(get_units_for_property(property_obj))
    if not units:
        return {
            "currency": property_obj.currency,
            "min_nightly_price": Decimal("0.000"),
            "min_monthly_price": Decimal("0.000"),
            "max_nightly_price": Decimal("0.000"),
            "max_monthly_price": Decimal("0.000"),
        }

    nightly_prices = []
    monthly_prices = []

    for unit in units:
        prices = get_effective_unit_prices(unit, stay_range)
        nightly_prices.append(prices["nightly_price"])
        monthly_prices.append(prices["monthly_price"])

    return {
        "currency": property_obj.currency,
        "min_nightly_price": min(nightly_prices) if nightly_prices else Decimal("0.000"),
        "min_monthly_price": min(monthly_prices) if monthly_prices else Decimal("0.000"),
        "max_nightly_price": max(nightly_prices) if nightly_prices else Decimal("0.000"),
        "max_monthly_price": max(monthly_prices) if monthly_prices else Decimal("0.000"),
    }


def build_property_recommendations(
    base_queryset,
    *,
    country: str = "",
    city: str = "",
    limit: int = 10,
    customer=None,
):
    qs = base_queryset
    if city:
        qs = qs.filter(city__iexact=city)
    elif country:
        qs = qs.filter(country__iexact=country)

    ordered = list(qs.order_by("-average_rating", "-total_reviews", "-created_at")[: max(limit * 4, 20)])
    if not customer:
        return ordered[:limit]

    favored_city = None
    favored_country = None
    liked_ids = set()
    amenity_terms: set[str] = set()
    try:
        wishlist_items = customer.wishlist.select_related("property_profile").all()[:50]
        if wishlist_items:
            first = wishlist_items[0].property_profile
            favored_city = (first.city or "").strip().lower()
            favored_country = (first.country or "").strip().lower()
        for wi in wishlist_items:
            liked_ids.add(wi.property_profile_id)
            for a in wi.property_profile.amenities.all()[:12]:
                if a.name_en:
                    amenity_terms.add(a.name_en.strip().lower())
    except Exception:
        pass

    try:
        reviews = customer.reviews.select_related("property_profile").filter(rating__gte=4)[:30]
        for rv in reviews:
            liked_ids.add(rv.property_profile_id)
            if not favored_city:
                favored_city = (rv.property_profile.city or "").strip().lower()
            if not favored_country:
                favored_country = (rv.property_profile.country or "").strip().lower()
    except Exception:
        pass

    scored = []
    for prop in ordered:
        score = float(getattr(prop, "average_rating", 0.0) or 0.0) * 10.0
        score += float(getattr(prop, "total_reviews", 0) or 0) * 0.2
        if favored_city and (prop.city or "").strip().lower() == favored_city:
            score += 20.0
        elif favored_country and (prop.country or "").strip().lower() == favored_country:
            score += 10.0
        if prop.id in liked_ids:
            score -= 6.0
        try:
            names = [a.name_en.strip().lower() for a in prop.amenities.all()[:15] if a.name_en]
            overlap = len(amenity_terms.intersection(set(names)))
            score += overlap * 2.5
        except Exception:
            pass
        scored.append((score, prop))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:limit]]


def build_search_suggestions(*, query: str, limit: int = 8) -> list[str]:
    term = (query or "").strip()
    if len(term) < 2:
        return []

    qs = PropertyProfile.objects.filter(is_active=True).filter(
        Q(name_en__icontains=term)
        | Q(name_ar__icontains=term)
        | Q(city__icontains=term)
        | Q(country__icontains=term)
        | Q(address_en__icontains=term)
        | Q(address_ar__icontains=term)
        | Q(property_number__icontains=term)
    )

    suggestions: list[str] = []
    seen = set()

    for p in qs.order_by("-created_at")[: max(20, limit * 2)]:
        for value in (p.name_en, p.city, p.country, p.property_number):
            cleaned = (value or "").strip()
            if not cleaned:
                continue
            key = cleaned.lower()
            if term.lower() in key and key not in seen:
                seen.add(key)
                suggestions.append(cleaned)
            if len(suggestions) >= limit:
                return suggestions

    # add lightweight landmark-style hints from common location words in address
    landmark_words = ["beach", "mall", "airport", "business", "city center", "marina"]
    for word in landmark_words:
        if term.lower() in word and word not in seen:
            suggestions.append(word.title())
        if len(suggestions) >= limit:
            break

    return suggestions
