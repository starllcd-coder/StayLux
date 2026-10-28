def can_manage_property(user, prop=None):
    """Property operators are distinct from individual apartment owners."""
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser:
        return True
    staff = getattr(user, "staff_profile", None)
    if not staff or not staff.is_active:
        return False
    if staff.role == "owner_admin":
        return True
    return staff.role == "manager" and (prop is None or staff.property_id == prop.pk)
