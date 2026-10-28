from typing import Iterable
from django.contrib import messages
from django.shortcuts import redirect


ROLE_OWNER_ADMIN = "owner_admin"
ROLE_MANAGER = "manager"
ROLE_RECEPTION = "reception"
ROLE_HOUSEKEEPING = "housekeeping"
ROLE_MAINTENANCE = "maintenance"
ROLE_ACCOUNTS = "accounts"

ROLES_ADMIN = {ROLE_OWNER_ADMIN, ROLE_MANAGER}
ROLES_RECEPTION = {ROLE_OWNER_ADMIN, ROLE_MANAGER, ROLE_RECEPTION}
ROLES_MAINTENANCE = {ROLE_OWNER_ADMIN, ROLE_MANAGER, ROLE_MAINTENANCE}
ROLES_MAINTENANCE_VIEW = {ROLE_OWNER_ADMIN, ROLE_MANAGER, ROLE_MAINTENANCE, ROLE_RECEPTION}
ROLES_HOUSEKEEPING = {ROLE_OWNER_ADMIN, ROLE_MANAGER, ROLE_HOUSEKEEPING}
ROLES_HOUSEKEEPING_VIEW = {ROLE_OWNER_ADMIN, ROLE_MANAGER, ROLE_HOUSEKEEPING, ROLE_RECEPTION}
ROLES_UNITS_MANAGE = {ROLE_OWNER_ADMIN, ROLE_MANAGER}
ROLES_UNITS_VIEW = {ROLE_OWNER_ADMIN, ROLE_MANAGER, ROLE_RECEPTION, ROLE_HOUSEKEEPING, ROLE_MAINTENANCE}
ROLES_BILLING = {ROLE_OWNER_ADMIN, ROLE_MANAGER, ROLE_RECEPTION, ROLE_ACCOUNTS}
ROLES_REPORTS = {ROLE_OWNER_ADMIN, ROLE_MANAGER, ROLE_ACCOUNTS}


def _get_user_role(user) -> str | None:
    from core.security import get_user_role
    return get_user_role(user)


def _has_role(user, roles: Iterable[str]) -> bool:
    role = _get_user_role(user)
    return bool(role and role in set(roles))


def _require_roles(request, roles: Iterable[str], message: str = "You do not have access to this page."):
    if request.user.is_superuser or _has_role(request.user, roles):
        return None
    messages.error(request, message)
    return redirect("dashboard")


def require_roles(roles: Iterable[str], message: str = "You do not have access to this page."):
    """Decorator for function-based views to enforce role membership.

    Usage:
        @login_required
        @require_roles(ROLES_RECEPTION)
        def my_view(request):
            ...
    """

    def decorator(view_func):
        def _wrapped(request, *args, **kwargs):
            if request.user.is_superuser or _has_role(request.user, roles):
                return view_func(request, *args, **kwargs)
            messages.error(request, message)
            return redirect("dashboard")

        _wrapped.__name__ = getattr(view_func, "__name__", "wrapped_view")
        return _wrapped

    return decorator


try:
    from rest_framework.permissions import BasePermission


    class RolePermission(BasePermission):
        """DRF permission class that looks for `required_roles` on the view.

        Set `required_roles = ROLES_RECEPTION` on a view or viewset to enforce.
        """

        def has_permission(self, request, view):
            required = getattr(view, "required_roles", None)
            if required is None:
                return True
            return request.user.is_superuser or _has_role(request.user, required)

except Exception:
    # DRF may not be importable in some tooling contexts; ignore then.
    pass
from rest_framework.permissions import BasePermission, SAFE_METHODS
from core.security import get_user_role

# Keep these aligned with accounts.models.StaffRole values
ROLE_OWNER_ADMIN = "owner_admin"
ROLE_MANAGER = "manager"
ROLE_RECEPTION = "reception"
ROLE_HOUSEKEEPING = "housekeeping"
ROLE_MAINTENANCE = "maintenance"


class IsStaffAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsOwnerOrManager(BasePermission):
    """
    Owner/Admin + Manager can do everything.
    Others read-only unless view allows.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        role = get_user_role(request.user)
        return role in {ROLE_OWNER_ADMIN, ROLE_MANAGER}


class IsReceptionOrHigher(BasePermission):
    """
    Reception + Manager + Owner/Admin can create/update bookings, guests, invoices, payments.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        role = get_user_role(request.user)
        return role in {ROLE_OWNER_ADMIN, ROLE_MANAGER, ROLE_RECEPTION}


class IsBillingStaff(BasePermission):
    def has_permission(self, request, view):
        role = get_user_role(request.user)
        if role not in ROLES_BILLING:
            return False
        if role == ROLE_ACCOUNTS and (request.method == "DELETE" or getattr(view, "action", "") in {"void", "refund"}):
            return False
        return True


class IsHousekeepingOrHigher(BasePermission):
    """
    Housekeeping + Manager + Owner/Admin can update housekeeping tasks.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        role = get_user_role(request.user)
        return role in {ROLE_OWNER_ADMIN, ROLE_MANAGER, ROLE_HOUSEKEEPING}


class IsMaintenanceOrHigher(BasePermission):
    """
    Maintenance + Manager + Owner/Admin can update maintenance requests.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        role = get_user_role(request.user)
        return role in {ROLE_OWNER_ADMIN, ROLE_MANAGER, ROLE_MAINTENANCE}
