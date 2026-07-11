from rest_framework import serializers
from django.db.models import Avg

from inventory.models import Amenity, Unit, UnitType
from mobile_api.discovery.models import PropertyExperienceMedia
from settings_app.models import PropertyProfile

from mobile_api.discovery.services import StayDateRange, get_effective_unit_prices, get_property_price_summary


class DiscoveryAmenitySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Amenity
        fields = [
            "id",
            "name_en",
            "name_ar",
            "name",
        ]

    def get_name(self, obj):
        request = self.context.get("request")
        lang = getattr(request, "LANGUAGE_CODE", "en") if request else "en"
        if str(lang).lower().startswith("ar") and obj.name_ar:
            return obj.name_ar
        return obj.name_en


class DiscoveryUnitTypeSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    amenities = DiscoveryAmenitySerializer(many=True, read_only=True)

    class Meta:
        model = UnitType
        fields = [
            "id",
            "business_type",
            "name_en",
            "name_ar",
            "name",
            "base_rate",
            "amenities",
        ]

    def get_name(self, obj):
        request = self.context.get("request")
        lang = getattr(request, "LANGUAGE_CODE", "en") if request else "en"
        if str(lang).lower().startswith("ar") and obj.name_ar:
            return obj.name_ar
        return obj.name_en


class PropertyListSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    display_address = serializers.SerializerMethodField()
    min_price = serializers.SerializerMethodField()
    max_price = serializers.SerializerMethodField()
    currency = serializers.CharField(read_only=True)
    available_unit_count = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()

    class Meta:
        model = PropertyProfile
        fields = [
            "id",
            "business_type",
            "name_en",
            "name_ar",
            "display_name",
            "city",
            "country",
            "display_address",
            "phone",
            "email",
            "currency",
            "min_price",
            "max_price",
            "available_unit_count",
            "average_rating",
            "total_reviews",
            "latitude",
            "longitude",
            "logo",
        ]

    def get_display_name(self, obj):
        request = self.context.get("request")
        lang = getattr(request, "LANGUAGE_CODE", "en") if request else "en"
        if str(lang).lower().startswith("ar") and obj.name_ar:
            return obj.name_ar
        return obj.name_en

    def get_display_address(self, obj):
        request = self.context.get("request")
        lang = getattr(request, "LANGUAGE_CODE", "en") if request else "en"
        if str(lang).lower().startswith("ar") and obj.address_ar:
            return obj.address_ar
        return obj.address_en

    def get_min_price(self, obj):
        stay_range = self.context.get("stay_range") or StayDateRange()
        summary = get_property_price_summary(obj, stay_range)
        if stay_range.nights >= 28:
            return summary["min_monthly_price"]
        return summary["min_nightly_price"]

    def get_max_price(self, obj):
        stay_range = self.context.get("stay_range") or StayDateRange()
        summary = get_property_price_summary(obj, stay_range)
        if stay_range.nights >= 28:
            return summary["max_monthly_price"]
        return summary["max_nightly_price"]

    def get_available_unit_count(self, obj):
        available_units = self.context.get("available_unit_count_map", {})
        return available_units.get(obj.id, getattr(obj, "active_unit_count", 0))

    def get_latitude(self, obj):
        return getattr(obj, "latitude", None)

    def get_longitude(self, obj):
        return getattr(obj, "longitude", None)

    def get_average_rating(self, obj):
        avg = getattr(obj, "average_rating", None)
        if avg is not None:
            return round(float(avg), 2)
        value = obj.reviews.filter(is_visible=True).aggregate(avg=Avg("rating")).get("avg")
        if value is None:
            return 0.0
        return round(float(value), 2)

    def get_total_reviews(self, obj):
        count = getattr(obj, "total_reviews", None)
        if count is not None:
            return int(count)
        return obj.reviews.filter(is_visible=True).count()


class PropertyDetailSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    display_address = serializers.SerializerMethodField()
    amenities = DiscoveryAmenitySerializer(many=True, read_only=True)
    unit_types = DiscoveryUnitTypeSerializer(many=True, read_only=True)
    price_summary = serializers.SerializerMethodField()
    total_units = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    media_gallery = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    virtual_tour_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyProfile
        fields = [
            "id",
            "business_type",
            "name_en",
            "name_ar",
            "display_name",
            "logo",
            "property_number",
            "city",
            "country",
            "phone",
            "whatsapp",
            "email",
            "address_en",
            "address_ar",
            "display_address",
            "currency",
            "latitude",
            "longitude",
            "amenities",
            "unit_types",
            "price_summary",
            "total_units",
            "media_gallery",
            "video_url",
            "virtual_tour_url",
        ]

    def get_display_name(self, obj):
        request = self.context.get("request")
        lang = getattr(request, "LANGUAGE_CODE", "en") if request else "en"
        if str(lang).lower().startswith("ar") and obj.name_ar:
            return obj.name_ar
        return obj.name_en

    def get_display_address(self, obj):
        request = self.context.get("request")
        lang = getattr(request, "LANGUAGE_CODE", "en") if request else "en"
        if str(lang).lower().startswith("ar") and obj.address_ar:
            return obj.address_ar
        return obj.address_en

    def get_price_summary(self, obj):
        stay_range = self.context.get("stay_range") or StayDateRange()
        summary = get_property_price_summary(obj, stay_range)
        return {
            "currency": summary["currency"],
            "min_nightly_price": summary["min_nightly_price"],
            "max_nightly_price": summary["max_nightly_price"],
            "min_monthly_price": summary["min_monthly_price"],
            "max_monthly_price": summary["max_monthly_price"],
        }

    def get_total_units(self, obj):
        return obj.units.filter(is_active=True).count()

    def get_latitude(self, obj):
        return getattr(obj, "latitude", None)

    def get_longitude(self, obj):
        return getattr(obj, "longitude", None)

    def get_media_gallery(self, obj):
        rows = obj.experience_media.filter(is_active=True).exclude(media_type=PropertyExperienceMedia.MediaType.IMAGE)
        images = obj.experience_media.filter(is_active=True, media_type=PropertyExperienceMedia.MediaType.IMAGE)
        media = list(images[:8]) + list(rows[:4])
        return [
            {
                "id": m.id,
                "type": m.media_type,
                "title": m.title,
                "url": m.url,
                "thumbnail_url": m.thumbnail_url,
            }
            for m in media
        ]

    def get_video_url(self, obj):
        row = obj.experience_media.filter(
            is_active=True,
            media_type=PropertyExperienceMedia.MediaType.VIDEO,
        ).first()
        return row.url if row else ""

    def get_virtual_tour_url(self, obj):
        row = obj.experience_media.filter(
            is_active=True,
            media_type=PropertyExperienceMedia.MediaType.TOUR,
        ).first()
        return row.url if row else ""


class UnitListSerializer(serializers.ModelSerializer):
    unit_type = DiscoveryUnitTypeSerializer(read_only=True)
    amenities = DiscoveryAmenitySerializer(many=True, read_only=True)
    pricing = serializers.SerializerMethodField()

    class Meta:
        model = Unit
        fields = [
            "id",
            "code",
            "floor",
            "category",
            "bed_config",
            "guest_capacity",
            "status",
            "unit_type",
            "amenities",
            "pricing",
        ]

    def get_pricing(self, obj):
        stay_range = self.context.get("stay_range") or StayDateRange()
        prices = get_effective_unit_prices(obj, stay_range)
        return {
            "booking_type": prices["booking_type"],
            "rent_cycle": prices["rent_cycle"],
            "nightly_price": prices["nightly_price"],
            "monthly_price": prices["monthly_price"],
            "estimated_total": prices["estimated_total"],
            "currency": obj.property_profile.currency,
        }
