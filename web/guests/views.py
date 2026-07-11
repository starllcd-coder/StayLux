from django.db.models import Q
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from core.viewsets import PropertyScopedModelViewSet
from core.permissions import IsReceptionOrHigher
from .models import Guest
from bookings.models import BookingType
from .serializers import GuestSerializer


class GuestViewSet(PropertyScopedModelViewSet):
    queryset = Guest.objects.select_related("property_profile").all()
    serializer_class = GuestSerializer
    permission_classes = [IsAuthenticatedOrReadOnly & IsReceptionOrHigher]
    property_field_name = "property_profile"

    def get_queryset(self):
        qs = super().get_queryset()
        prop = self.get_property_profile()
        if prop:
            booking_type = BookingType.HOTEL if prop.business_type == "hotel" else BookingType.APARTMENT
            other_type = BookingType.APARTMENT if booking_type == BookingType.HOTEL else BookingType.HOTEL
            qs = qs.filter(property_profile=prop)
            qs = qs.exclude(bookings__booking_type=other_type)
            qs = qs.filter(bookings__booking_type=booking_type).distinct()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(full_name__icontains=q) | Q(phone__icontains=q) | Q(id_number__icontains=q))
        return qs