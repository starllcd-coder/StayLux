from rest_framework import serializers

from mobile_api.concierge.models import ConciergeRequest, ConciergeService


class ConciergeServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConciergeService
        fields = ["id", "code", "name", "description", "base_price", "is_active"]


class ConciergeRequestSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = ConciergeRequest
        fields = [
            "id",
            "service",
            "service_name",
            "property_profile",
            "requested_for_date",
            "notes",
            "quote_amount",
            "status",
            "created_at",
        ]
        read_only_fields = ["quote_amount", "status", "created_at"]
