from rest_framework import serializers
from .models import MaintenanceRequest


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRequest
        fields = [
            "id",
            "property_profile",
            "unit",
            "reported_by",
            "assigned_to",
            "status",
            "priority",
            "maintenance_type",
            "title",
            "description",
            "before_photo",
            "after_photo",
            "material_cost",
            "labor_cost",
            "total_cost",
            "completed_notes",
            "completed_at",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")