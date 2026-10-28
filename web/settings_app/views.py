from rest_framework import viewsets, permissions
from .models import PropertyProfile
from .serializers import PropertyProfileSerializer
from .access import can_manage_property


class PropertyAccessPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if view.action == "create":
            staff = getattr(request.user, "staff_profile", None)
            return bool(request.user.is_superuser or (staff and staff.is_active and staff.role == "owner_admin"))
        return can_manage_property(request.user)

    def has_object_permission(self, request, view, obj):
        return request.method in permissions.SAFE_METHODS or can_manage_property(request.user, obj)

class PropertyProfileViewSet(viewsets.ModelViewSet):
    queryset = PropertyProfile.objects.all()
    serializer_class = PropertyProfileSerializer
    permission_classes = [PropertyAccessPermission]

    def get_queryset(self):
        user = self.request.user
        staff = getattr(user, "staff_profile", None)
        if user.is_superuser or (staff and staff.is_active and staff.role == "owner_admin"):
            return super().get_queryset()
        if staff and staff.is_active:
            return super().get_queryset().filter(pk=staff.property_id)
        owner = getattr(user, "owner_profile", None)
        return super().get_queryset().filter(pk=owner.property_id) if owner and owner.is_active else super().get_queryset().none()

    def destroy(self, request, *args, **kwargs):
        # Use the web confirmation flow for permanent property deletion.
        from rest_framework.response import Response
        self.get_object()
        return Response({"detail": "Delete properties through Settings with name confirmation."}, status=405)
