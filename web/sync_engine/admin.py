from django.contrib import admin

from sync_engine.models import SyncConfig, SyncEvent, SyncInboundEvent


@admin.register(SyncConfig)
class SyncConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "enabled", "mode", "remote_base_url", "push_enabled", "interval_seconds", "last_sync_at")


@admin.register(SyncEvent)
class SyncEventAdmin(admin.ModelAdmin):
    list_display = ("event_uuid", "model_label", "object_pk", "operation", "status", "attempts", "created_at")
    list_filter = ("status", "operation", "model_label")
    search_fields = ("model_label", "object_pk")


@admin.register(SyncInboundEvent)
class SyncInboundEventAdmin(admin.ModelAdmin):
    list_display = ("event_uuid", "source_node", "is_processed", "created_at")
    list_filter = ("is_processed",)
    search_fields = ("event_uuid", "source_node")
