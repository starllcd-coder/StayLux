from __future__ import annotations

import uuid

from django.db import models

from core.models import TimeStampedModel


class SyncMode(models.TextChoices):
    OFFLINE = "offline", "Offline"
    ONLINE = "online", "Online"
    AUTO = "auto", "Auto"


class SyncEventStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SYNCED = "synced", "Synced"
    FAILED = "failed", "Failed"


class SyncConfig(TimeStampedModel):
    """
    Singleton sync configuration stored in local desktop DB.
    """

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    enabled = models.BooleanField(default=True)
    mode = models.CharField(max_length=20, choices=SyncMode.choices, default=SyncMode.AUTO)

    remote_base_url = models.CharField(max_length=255, blank=True, default="")
    api_token = models.CharField(max_length=255, blank=True, default="")
    shared_secret = models.CharField(max_length=255, blank=True, default="")

    push_enabled = models.BooleanField(default=True)
    pull_enabled = models.BooleanField(default=False)
    interval_seconds = models.PositiveIntegerField(default=30)
    max_retry_attempts = models.PositiveIntegerField(default=8)
    conflict_policy = models.CharField(max_length=30, default="last_write_wins")

    node_id = models.CharField(max_length=100, blank=True, default="")
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_pull_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Sync Configuration"
        verbose_name_plural = "Sync Configuration"

    def __str__(self):
        return f"SyncConfig(mode={self.mode}, enabled={self.enabled})"


class SyncEvent(TimeStampedModel):
    event_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    source_node = models.CharField(max_length=100, blank=True, default="")

    model_label = models.CharField(max_length=120)
    object_pk = models.CharField(max_length=80)
    operation = models.CharField(max_length=20)  # create | update | delete
    payload = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=20, choices=SyncEventStatus.choices, default=SyncEventStatus.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    is_dead_letter = models.BooleanField(default=False)
    synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["model_label", "object_pk"]),
            models.Index(fields=["is_dead_letter", "next_retry_at"]),
        ]

    def __str__(self):
        return f"{self.model_label}:{self.object_pk} {self.operation} ({self.status})"


class SyncInboundEvent(TimeStampedModel):
    event_uuid = models.UUIDField()
    source_node = models.CharField(max_length=100, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    is_processed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("event_uuid", "source_node")
        indexes = [
            models.Index(fields=["is_processed", "created_at"]),
        ]

    def __str__(self):
        return f"Inbound {self.event_uuid} from {self.source_node or 'unknown'}"
