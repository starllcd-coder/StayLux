from rest_framework import viewsets, permissions
from .models import StaffProfile
from .serializers import StaffProfileSerializer

class StaffProfileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StaffProfile.objects.select_related("user", "property").all()
    serializer_class = StaffProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return super().get_queryset()
        staff = getattr(self.request.user, "staff_profile", None)
        if not staff or not staff.is_active:
            return super().get_queryset().none()
        qs = super().get_queryset().filter(property_id=staff.property_id)
        return qs if staff.role in {"owner_admin", "manager"} else qs.filter(pk=staff.pk)
