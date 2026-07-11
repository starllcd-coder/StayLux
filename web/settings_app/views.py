from rest_framework import viewsets, permissions
from .models import PropertyProfile
from .serializers import PropertyProfileSerializer

class PropertyProfileViewSet(viewsets.ModelViewSet):
    queryset = PropertyProfile.objects.all()
    serializer_class = PropertyProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
