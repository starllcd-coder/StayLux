from __future__ import annotations
from typing import Optional, Dict, Any

from django.contrib.auth import get_user_model
from settings_app.models import PropertyProfile
from .models import AuditLog, AuditAction

User = get_user_model()


def log_action(
    *,
    property_profile: PropertyProfile,
    actor: Optional[User],
    object_type: str,
    object_id: str,
    action: str,
    message: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    return AuditLog.objects.create(
        property_profile=property_profile,
        actor=actor,
        object_type=object_type,
        object_id=str(object_id),
        action=action,
        message=message,
        metadata=metadata or {},
    )