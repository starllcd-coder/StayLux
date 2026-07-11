from django.contrib import admin
from .models import NotificationSetting, WhatsAppTemplate, OutboxMessage


@admin.register(NotificationSetting)
class NotificationSettingAdmin(admin.ModelAdmin):
    list_display = ("property_profile", "enable_whatsapp", "default_channel", "updated_at")


@admin.register(WhatsAppTemplate)
class WhatsAppTemplateAdmin(admin.ModelAdmin):
    list_display = ("property_profile", "key", "language", "is_active", "updated_at")
    list_filter = ("property_profile", "language", "is_active")
    search_fields = ("key", "body")


@admin.register(OutboxMessage)
class OutboxMessageAdmin(admin.ModelAdmin):
    list_display = ("property_profile", "channel", "status", "event_key", "to_phone", "created_at")
    list_filter = ("property_profile", "channel", "status")
    search_fields = ("to_phone", "to_email", "event_key", "content")