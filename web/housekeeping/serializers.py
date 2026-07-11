from rest_framework import serializers
from .models import HousekeepingTask


class HousekeepingTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = HousekeepingTask
        fields = [
            "id",
            "property_profile",
            "unit",
            "booking",
            "assigned_to",
            "status",
            "priority",
            "title",
            "notes",
            "due_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")