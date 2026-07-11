from __future__ import annotations

from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError

from core.models import TimeStampedModel
from settings_app.models import PropertyProfile
from inventory.models import UnitType, Unit


class RatePlanScope(models.TextChoices):
    UNIT_TYPE = "unit_type", "Unit Type"
    UNIT = "unit", "Unit"


class RatePlan(TimeStampedModel):
    """
    Base plan for pricing. Seasonal rules override this plan.
    """
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="rate_plans")

    name = models.CharField(max_length=120)
    scope = models.CharField(max_length=20, choices=RatePlanScope.choices, default=RatePlanScope.UNIT_TYPE)

    unit_type = models.ForeignKey(UnitType, on_delete=models.CASCADE, null=True, blank=True, related_name="rate_plans")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, null=True, blank=True, related_name="rate_plans")

    currency = models.CharField(max_length=10, default="OMR")
    base_price_nightly = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    base_price_monthly = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["property_profile", "is_active"]),
            models.Index(fields=["property_profile", "scope"]),
        ]

    def __str__(self):
        return f"{self.name}"

    def clean(self):
        if self.scope == RatePlanScope.UNIT_TYPE and not self.unit_type_id:
            raise ValidationError("unit_type is required when scope=unit_type")
        if self.scope == RatePlanScope.UNIT and not self.unit_id:
            raise ValidationError("unit is required when scope=unit")
        if self.unit_type_id and self.unit_type.property_profile_id != self.property_profile_id:
            raise ValidationError("unit_type.property_profile mismatch")
        if self.unit_id and self.unit.property_profile_id != self.property_profile_id:
            raise ValidationError("unit.property_profile mismatch")


class SeasonalRateRule(TimeStampedModel):
    """
    Override pricing for specific date ranges and optional weekdays.
    Priority: higher wins.
    """
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="seasonal_rates")

    rate_plan = models.ForeignKey(RatePlan, on_delete=models.CASCADE, related_name="seasonal_rules")

    date_from = models.DateField()
    date_to = models.DateField()

    # "0,1,2,3,4,5,6" where Monday=0 ... Sunday=6
    weekdays = models.CharField(max_length=20, blank=True, default="")

    price_nightly = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    price_monthly = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)

    priority = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-priority", "-created_at"]
        indexes = [
            models.Index(fields=["property_profile", "is_active"]),
            models.Index(fields=["property_profile", "date_from", "date_to"]),
        ]

    def __str__(self):
        return f"{self.rate_plan.name} ({self.date_from}..{self.date_to})"

    def clean(self):
        if self.rate_plan.property_profile_id != self.property_profile_id:
            raise ValidationError("rate_plan.property_profile mismatch")
        if self.date_to < self.date_from:
            raise ValidationError("date_to must be >= date_from")


class DynamicPricingRule(TimeStampedModel):
    """
    Lightweight auto-pricing configuration per property.
    Suggestion endpoint uses these multipliers for demand-aware recommendations.
    """

    property_profile = models.OneToOneField(
        PropertyProfile,
        on_delete=models.CASCADE,
        related_name="dynamic_pricing_rule",
    )
    is_enabled = models.BooleanField(default=True)

    base_adjustment_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    weekend_adjustment_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("8.00"))

    high_occupancy_threshold = models.PositiveSmallIntegerField(default=80)
    high_occupancy_adjustment_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("12.00"))

    low_occupancy_threshold = models.PositiveSmallIntegerField(default=40)
    low_occupancy_adjustment_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("-8.00"))

    seasonal_peak_months = models.CharField(max_length=40, blank=True, default="6,7,8,12")
    seasonal_peak_adjustment_pct = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("10.00"))

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["is_enabled"]),
        ]

    def __str__(self):
        return f"DynamicPricingRule({self.property_profile_id})"
