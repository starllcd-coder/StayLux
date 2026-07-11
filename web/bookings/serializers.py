from rest_framework import serializers
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    total_estimated = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "property_profile",
            "guest",
            "unit",

            "booking_type",
            "rent_cycle",
            "status",
            "start_date",
            "end_date",
            "adults",
            "children",

            "rate",
            "discount",
            "deposit",

            "price_locked",
            "locked_at",
            "locked_rate",
            "locked_discount",
            "locked_deposit",
            "locked_total",

            "is_archived",
            "archived_at",

            "notes",
            "total_estimated",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "price_locked",
            "locked_at",
            "locked_rate",
            "locked_discount",
            "locked_deposit",
            "locked_total",
            "archived_at",
            "total_estimated",
            "created_at",
            "updated_at",
        )

    def get_total_estimated(self, obj: Booking):
        return str(obj.estimate_total())