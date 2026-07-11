from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Amenity, UnitType, Unit
from .serializers import AmenitySerializer, UnitTypeSerializer, UnitSerializer
from settings_app.models import PropertyProfile


class AmenityViewSet(viewsets.ModelViewSet):
    queryset = Amenity.objects.select_related("property_profile").all()
    serializer_class = AmenitySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        prop = self.request.query_params.get("property_profile")
        if prop:
            qs = qs.filter(property_profile_id=prop)
        return qs


class UnitTypeViewSet(viewsets.ModelViewSet):
    queryset = UnitType.objects.select_related("property_profile").all()
    serializer_class = UnitTypeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        prop = self.request.query_params.get("property_profile")
        if prop:
            qs = qs.filter(property_profile_id=prop)
            prop_obj = PropertyProfile.objects.filter(id=prop).first()
            if prop_obj:
                qs = qs.filter(business_type=prop_obj.business_type)
        business_type = self.request.query_params.get("business_type")
        if business_type:
            qs = qs.filter(business_type=business_type)
        return qs


class UnitViewSet(viewsets.ModelViewSet):
    queryset = Unit.objects.select_related("property_profile", "unit_type").all()
    serializer_class = UnitSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        prop = self.request.query_params.get("property_profile")
        if prop:
            qs = qs.filter(property_profile_id=prop)
            prop_obj = PropertyProfile.objects.filter(id=prop).first()
            if prop_obj:
                qs = qs.filter(unit_type__business_type=prop_obj.business_type)
        business_type = self.request.query_params.get("business_type")
        if business_type:
            qs = qs.filter(unit_type__business_type=business_type)
        return qs