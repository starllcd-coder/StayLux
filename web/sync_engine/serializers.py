from __future__ import annotations

from rest_framework import serializers

from sync_engine.models import SyncConfig, SyncEvent


class SyncConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncConfig
        fields = [
            "enabled",
            "mode",
            "remote_base_url",
            "api_token",
            "shared_secret",
            "push_enabled",
            "pull_enabled",
            "interval_seconds",
            "max_retry_attempts",
            "conflict_policy",
            "node_id",
            "last_sync_at",
            "last_success_at",
            "last_pull_at",
            "last_error",
            "updated_at",
        ]
        read_only_fields = [
            "last_sync_at",
            "last_success_at",
            "last_error",
            "updated_at",
        ]


class SyncEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncEvent
        fields = [
            "event_uuid",
            "source_node",
            "model_label",
            "object_pk",
            "operation",
            "payload",
            "status",
            "attempts",
            "last_attempt_at",
            "next_retry_at",
            "is_dead_letter",
            "synced_at",
            "last_error",
            "created_at",
        ]


class InboundSyncSerializer(serializers.Serializer):
    source_node = serializers.CharField(required=False, allow_blank=True, default="")
    events = serializers.ListField(child=serializers.DictField(), allow_empty=True)
