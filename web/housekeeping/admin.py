from django.contrib import admin
from .models import HousekeepingTask


@admin.register(HousekeepingTask)
class HousekeepingTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "property_profile", "unit", "status", "priority", "assigned_to", "created_at")
    list_filter = ("property_profile", "status", "priority")
    search_fields = ("unit__code", "title", "notes")