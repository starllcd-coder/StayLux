from rest_framework import viewsets, permissions
from .models import StaffProfile
from .serializers import StaffProfileSerializer

class StaffProfileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StaffProfile.objects.select_related("user", "property").all()
    serializer_class = StaffProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
