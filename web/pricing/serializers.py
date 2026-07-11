from rest_framework import serializers
from .models import DynamicPricingRule, RatePlan, SeasonalRateRule


class RatePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = RatePlan
        fields = [
            "id",
            "property_profile",
            "name",
            "scope",
            "unit_type",
            "unit",
            "currency",
            "base_price_nightly",
            "base_price_monthly",
            "is_active",
            "created_at",
            "updated_at",
        ]


class SeasonalRateRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeasonalRateRule
        fields = [
            "id",
            "property_profile",
            "rate_plan",
            "date_from",
            "date_to",
            "weekdays",
            "price_nightly",
            "price_monthly",
            "priority",
            "is_active",
            "created_at",
            "updated_at",
        ]


class DynamicPricingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DynamicPricingRule
        fields = [
            "id",
            "property_profile",
            "is_enabled",
            "base_adjustment_pct",
            "weekend_adjustment_pct",
            "high_occupancy_threshold",
            "high_occupancy_adjustment_pct",
            "low_occupancy_threshold",
            "low_occupancy_adjustment_pct",
            "seasonal_peak_months",
            "seasonal_peak_adjustment_pct",
            "created_at",
            "updated_at",
        ]
