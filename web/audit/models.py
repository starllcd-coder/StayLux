from django.db import models
from django.contrib.auth import get_user_model

from core.models import TimeStampedModel
from settings_app.models import PropertyProfile

User = get_user_model()


class AuditAction(models.TextChoices):
    CREATE = "create", "Create"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"
    STATUS_CHANGE = "status_change", "Status Change"
    ASSIGN = "assign", "Assign"


class AuditLog(TimeStampedModel):
    """
    Simple audit trail (Phase A):
    - property_profile
    - actor (user)
    - object_type + object_id
    - action + message + metadata json
    """
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="audit_logs")
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs")

    object_type = models.CharField(max_length=80)     # e.g. booking, invoice, housekeeping_task
    object_id = models.CharField(max_length=80)       # store as string (supports UUID in future)

    action = models.CharField(max_length=30, choices=AuditAction.choices)
    message = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property_profile", "created_at"]),
            models.Index(fields=["object_type", "object_id"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.object_type} {self.object_id} {self.action}"