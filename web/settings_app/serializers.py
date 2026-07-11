from rest_framework import serializers
from .models import PropertyProfile

class PropertyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyProfile
        fields = [
            "id",
            "business_type",
            "name_en",
            "name_ar",
            "logo",
            "phone",
            "whatsapp",
            "email",
            "address_en",
            "address_ar",
            "vat_no",
            "cr_no",
            "receipt_footer_en",
            "receipt_footer_ar",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
