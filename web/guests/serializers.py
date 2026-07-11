from rest_framework import serializers
from .models import Guest


class GuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guest
        fields = [
            "id",
            "property_profile",
            "business_type",
            "full_name",
            "phone",
            "whatsapp",
            "email",
            "nationality",
            "id_type",
            "id_number",
            "id_expiry",
            "id_document",
            "address",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")