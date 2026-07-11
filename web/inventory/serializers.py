from rest_framework import serializers
from .models import Amenity, UnitType, Unit


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = [
            "id",
            "property_profile",
            "name_en",
            "name_ar",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")


class UnitTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitType
        fields = [
            "id",
            "property_profile",
            "business_type",
            "name_en",
            "name_ar",
            "base_rate",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")


class UnitSerializer(serializers.ModelSerializer):
    unit_type_name_en = serializers.CharField(source="unit_type.name_en", read_only=True)
    amenities = serializers.PrimaryKeyRelatedField(many=True, queryset=Amenity.objects.all(), required=False)

    class Meta:
        model = Unit
        fields = [
            "id",
            "property_profile",
            "unit_type",
            "unit_type_name_en",
            "code",
            "floor",
            "category",
            "bed_config",
            "guest_capacity",
            "daily_price",
            "monthly_price",
            "seasonal_price",
            "amenities",
            "status",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")