from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.db import models
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from core.viewsets import PropertyScopedModelViewSet
from core.permissions import IsReceptionOrHigher
from bookings.models import Booking, BookingStatus
from inventory.models import Unit

from .models import DynamicPricingRule, RatePlan, SeasonalRateRule
from .serializers import DynamicPricingRuleSerializer, RatePlanSerializer, SeasonalRateRuleSerializer


class RatePlanViewSet(PropertyScopedModelViewSet):
    queryset = RatePlan.objects.select_related("property_profile", "unit_type", "unit").all()
    serializer_class = RatePlanSerializer
    permission_classes = [IsAuthenticatedOrReadOnly & IsReceptionOrHigher]
    property_field_name = "property_profile"

    def get_queryset(self):
        qs = super().get_queryset()
        prop = self.get_property_profile()
        if prop:
            qs = qs.filter(
                models.Q(unit_type__business_type=prop.business_type)
                | models.Q(unit__unit_type__business_type=prop.business_type)
            )
        return qs


class SeasonalRateRuleViewSet(PropertyScopedModelViewSet):
    queryset = SeasonalRateRule.objects.select_related("property_profile", "rate_plan").all()
    serializer_class = SeasonalRateRuleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly & IsReceptionOrHigher]
    property_field_name = "property_profile"

    def get_queryset(self):
        qs = super().get_queryset()
        prop = self.get_property_profile()
        if prop:
            qs = qs.filter(
                models.Q(rate_plan__unit_type__business_type=prop.business_type)
                | models.Q(rate_plan__unit__unit_type__business_type=prop.business_type)
            )
        return qs


class DynamicPricingRuleViewSet(PropertyScopedModelViewSet):
    queryset = DynamicPricingRule.objects.select_related("property_profile").all()
    serializer_class = DynamicPricingRuleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly & IsReceptionOrHigher]
    property_field_name = "property_profile"


class DynamicPricingSuggestionView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly & IsReceptionOrHigher]

    def get(self, request, *args, **kwargs):
        unit_id = request.query_params.get("unit_id")
        target_date_str = request.query_params.get("date", "")

        if not unit_id:
            return Response({"detail": "unit_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        unit = Unit.objects.select_related("property_profile").filter(id=unit_id, is_active=True).first()
        if not unit:
            return Response({"detail": "Unit not found"}, status=status.HTTP_404_NOT_FOUND)

        target_date = date.today()
        if target_date_str:
            try:
                target_date = date.fromisoformat(target_date_str)
            except ValueError:
                return Response({"detail": "date must be YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        prop = unit.property_profile
        rule = DynamicPricingRule.objects.filter(property_profile=prop).first()
        base_price = unit.daily_price or Decimal("0.000")

        occupied_units = Booking.objects.filter(
            property_profile=prop,
            status__in=[BookingStatus.RESERVED, BookingStatus.CHECKED_IN],
            start_date__lt=target_date + timedelta(days=1),
            end_date__gt=target_date,
        ).values("unit_id").distinct().count()

        total_units = prop.units.filter(is_active=True).count() or 1
        occupancy_pct = int(round((occupied_units / total_units) * 100))

        adjustments = []
        pct = Decimal("0.00")

        if rule and rule.is_enabled:
            pct += rule.base_adjustment_pct
            if rule.base_adjustment_pct != 0:
                adjustments.append({"reason": "base_adjustment", "pct": str(rule.base_adjustment_pct)})

            if target_date.weekday() >= 4:
                pct += rule.weekend_adjustment_pct
                adjustments.append({"reason": "weekend_adjustment", "pct": str(rule.weekend_adjustment_pct)})

            peak_months = {m.strip() for m in (rule.seasonal_peak_months or "").split(",") if m.strip()}
            if str(target_date.month) in peak_months:
                pct += rule.seasonal_peak_adjustment_pct
                adjustments.append({"reason": "seasonal_peak", "pct": str(rule.seasonal_peak_adjustment_pct)})

            if occupancy_pct >= int(rule.high_occupancy_threshold):
                pct += rule.high_occupancy_adjustment_pct
                adjustments.append({"reason": "high_occupancy", "pct": str(rule.high_occupancy_adjustment_pct)})
            elif occupancy_pct <= int(rule.low_occupancy_threshold):
                pct += rule.low_occupancy_adjustment_pct
                adjustments.append({"reason": "low_occupancy", "pct": str(rule.low_occupancy_adjustment_pct)})
        else:
            # fallback heuristics when explicit rule is not yet set
            if target_date.weekday() >= 4:
                pct += Decimal("8.00")
                adjustments.append({"reason": "weekend_adjustment", "pct": "8.00"})
            if occupancy_pct >= 80:
                pct += Decimal("10.00")
                adjustments.append({"reason": "high_occupancy", "pct": "10.00"})
            elif occupancy_pct <= 40:
                pct += Decimal("-7.00")
                adjustments.append({"reason": "low_occupancy", "pct": "-7.00"})

        multiplier = (Decimal("100.00") + pct) / Decimal("100.00")
        suggested_price = (base_price * multiplier).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

        return Response(
            {
                "unit_id": unit.id,
                "property_profile": prop.id,
                "date": target_date.isoformat(),
                "currency": prop.currency,
                "base_price_nightly": str(base_price),
                "occupancy_pct": occupancy_pct,
                "total_adjustment_pct": str(pct),
                "suggested_price_nightly": str(suggested_price),
                "adjustments": adjustments,
                "rule_configured": bool(rule and rule.is_enabled),
            },
            status=status.HTTP_200_OK,
        )


class AvailabilitySuggestionView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly & IsReceptionOrHigher]

    def get(self, request, *args, **kwargs):
        property_id = request.query_params.get("property_profile")
        if not property_id:
            return Response({"detail": "property_profile is required"}, status=status.HTTP_400_BAD_REQUEST)

        unit_count = Unit.objects.filter(property_profile_id=property_id, is_active=True).count()
        if unit_count == 0:
            return Response({"detail": "No active units found"}, status=status.HTTP_404_NOT_FOUND)

        today = date.today()
        rows = []
        for i in range(14):
            day = today + timedelta(days=i)
            booked_units = Booking.objects.filter(
                property_profile_id=property_id,
                status__in=[BookingStatus.RESERVED, BookingStatus.CHECKED_IN],
                start_date__lt=day + timedelta(days=1),
                end_date__gt=day,
            ).values("unit_id").distinct().count()
            occupancy_pct = int(round((booked_units / unit_count) * 100))
            if occupancy_pct >= 85:
                signal = "high-demand"
                suggestion = "Increase price window or enforce minimum stay."
            elif occupancy_pct <= 35:
                signal = "low-demand"
                suggestion = "Apply promotion or lower rate for conversion."
            else:
                signal = "balanced"
                suggestion = "Keep standard pricing."
            rows.append(
                {
                    "date": day.isoformat(),
                    "booked_units": booked_units,
                    "total_units": unit_count,
                    "occupancy_pct": occupancy_pct,
                    "signal": signal,
                    "suggestion": suggestion,
                }
            )

        return Response({"results": rows}, status=status.HTTP_200_OK)


class BulkSeasonalRateUpdateView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly & IsReceptionOrHigher]

    def post(self, request, *args, **kwargs):
        property_id = request.data.get("property_profile")
        rate_plan_id = request.data.get("rate_plan")
        date_from = request.data.get("date_from")
        date_to = request.data.get("date_to")
        price_nightly = request.data.get("price_nightly")
        price_monthly = request.data.get("price_monthly")
        weekdays = (request.data.get("weekdays") or "").strip()
        priority = int(request.data.get("priority") or 0)

        if not property_id or not date_from or not date_to:
            return Response(
                {"detail": "property_profile, date_from and date_to are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plans_qs = RatePlan.objects.filter(property_profile_id=property_id, is_active=True)
        if rate_plan_id:
            plans_qs = plans_qs.filter(id=rate_plan_id)
        plans = list(plans_qs[:200])
        if not plans:
            return Response({"detail": "No active rate plan found"}, status=status.HTTP_404_NOT_FOUND)

        created = 0
        for plan in plans:
            SeasonalRateRule.objects.create(
                property_profile_id=property_id,
                rate_plan=plan,
                date_from=date_from,
                date_to=date_to,
                weekdays=weekdays,
                price_nightly=price_nightly if price_nightly not in ("", None) else None,
                price_monthly=price_monthly if price_monthly not in ("", None) else None,
                priority=priority,
                is_active=True,
            )
            created += 1

        return Response(
            {
                "message": "Bulk seasonal pricing update applied.",
                "created_rules": created,
            },
            status=status.HTTP_201_CREATED,
        )
