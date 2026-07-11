from django.contrib import admin
from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "property_profile",
        "unit",
        "guest",
        "booking_type",
        "rent_cycle",
        "status",
        "start_date",
        "end_date",
        "created_at",
    )
    list_filter = ("property_profile", "booking_type", "rent_cycle", "status")
    search_fields = ("guest__full_name", "guest__phone", "unit__code")