from rest_framework.permissions import IsAuthenticatedOrReadOnly

from core.viewsets import PropertyScopedModelViewSet
from core.permissions import IsReceptionOrHigher

from .models import RatePlan, SeasonalRateRule
from .serializers import RatePlanSerializer, SeasonalRateRuleSerializer


class RatePlanViewSet(PropertyScopedModelViewSet):
    queryset = RatePlan.objects.select_related("property_profile", "unit_type", "unit").all()
    serializer_class = RatePlanSerializer
    permission_classes = [IsAuthenticatedOrReadOnly & IsReceptionOrHigher]
    property_field_name = "property_profile"


class SeasonalRateRuleViewSet(PropertyScopedModelViewSet):
    queryset = SeasonalRateRule.objects.select_related("property_profile", "rate_plan").all()
    serializer_class = SeasonalRateRuleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly & IsReceptionOrHigher]
    property_field_name = "property_profile"