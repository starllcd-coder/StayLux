from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsMobileCustomer(BasePermission):
    """
    Allows access only to authenticated users linked to a mobile customer profile.
    """

    message = "You must be signed in as a mobile customer to access this resource."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        return hasattr(user, "mobile_customer")


class IsAuthenticatedOrMobileReadOnly(BasePermission):
    """
    Public read access for discovery endpoints, auth required for writes.
    """

    message = "Authentication is required for this action."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated)