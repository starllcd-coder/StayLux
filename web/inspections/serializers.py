from rest_framework import serializers
from .models import MoveOutInspection


class MoveOutInspectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoveOutInspection
        fields = [
            "id",
            "property_profile",
            "contract",
            "status",
            "inspection_date",
            "keys_returned",
            "unit_clean",
            "no_damage",
            "deductions",
            "notes",
            "refundable_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("refundable_amount", "created_at", "updated_at")