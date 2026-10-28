from __future__ import annotations

from settings_app.models import PropertyProfile
from notifications.models import OutboxMessage
from core.permissions import ROLE_OWNER_ADMIN
from core.security import get_user_role


def notification_badge(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {
            "unread_count": 0,
            "latest_notifications": [],
            "active_property": None,
            "property_switcher_items": [],
            "can_switch_properties": False,
        }

    prop = None
    staff = getattr(request.user, "staff_profile", None)
    if staff and staff.is_active and not request.user.is_superuser and staff.role != ROLE_OWNER_ADMIN:
        prop = staff.property
    prop_id = request.session.get("active_property_id")
    if prop_id and prop is None:
        try:
            prop = PropertyProfile.objects.get(id=prop_id)
        except PropertyProfile.DoesNotExist:
            prop = None
    staff = getattr(request.user, "staff_profile", None)
    if staff and staff.is_active and not request.user.is_superuser and staff.role != ROLE_OWNER_ADMIN:
        prop = staff.property
    if prop is None:
        prop = PropertyProfile.objects.first()

    if not prop:
        return {
            "unread_count": 0,
            "latest_notifications": [],
            "active_property": None,
            "property_switcher_items": [],
            "can_switch_properties": False,
        }

    unread_qs = OutboxMessage.objects.filter(property_profile=prop, is_read=False).order_by("-created_at")
    unread_count = unread_qs.count()
    latest_notifications = list(unread_qs[:5])
    can_switch = bool(request.user.is_superuser or get_user_role(request.user) == ROLE_OWNER_ADMIN)
    switcher_items = list(PropertyProfile.objects.filter(is_active=True).order_by("name_en", "id")) if can_switch else []

    return {
        "unread_count": unread_count,
        "latest_notifications": latest_notifications,
        "active_property": prop,
        "property_switcher_items": switcher_items,
        "can_switch_properties": can_switch,
    }
