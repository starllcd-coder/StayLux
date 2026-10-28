from __future__ import annotations

from typing import Optional
from django.contrib.auth.models import AnonymousUser


def get_user_staff_profile(user):
    if not user or isinstance(user, AnonymousUser):
        return None
    # accounts.StaffProfile is OneToOne with user in your backend
    return getattr(user, "staff_profile", None)


def get_user_property_profile_id(user) -> Optional[int]:
    sp = get_user_staff_profile(user)
    if not sp:
        owner = getattr(user, "owner_profile", None)
        return owner.property_id if owner else None
    return sp.property_id


def get_user_role(user) -> Optional[str]:
    if not user or not user.is_authenticated or not user.is_active:
        return None
    if user.is_superuser:
        return "owner_admin"
    sp = get_user_staff_profile(user)
    if not sp:
        owner = getattr(user, "owner_profile", None)
        return "owner" if owner and owner.is_active else None
    return sp.role if sp.is_active else None
