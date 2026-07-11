from django.contrib import admin
from .models import Guest


@admin.register(Guest)
class GuestAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "property_profile",
        "phone",
        "nationality",
        "id_type",
        "id_number",
        "is_active",
        "created_at",
    )
    list_filter = ("property_profile", "nationality", "id_type", "is_active")
    search_fields = ("full_name", "phone", "email", "id_number")