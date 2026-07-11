from django.contrib import admin
from .models import MaintenanceRequest


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "property_profile", "unit", "status", "priority", "assigned_to", "created_at")
    list_filter = ("property_profile", "status", "priority")
    search_fields = ("unit__code", "title", "description")