from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "property_profile", "actor", "object_type", "object_id", "action", "message")
    list_filter = ("property_profile", "action", "object_type")
    search_fields = ("object_type", "object_id", "message", "actor__username")