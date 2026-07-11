from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from mobile_api.concierge.models import ConciergeRequest, ConciergeService
from mobile_api.concierge.serializers import ConciergeRequestSerializer, ConciergeServiceSerializer
from mobile_api.permissions import IsMobileCustomer


class ConciergeServiceListView(APIView):
    permission_classes = [IsMobileCustomer]

    def get(self, request, *args, **kwargs):
        qs = ConciergeService.objects.filter(is_active=True)
        return Response(ConciergeServiceSerializer(qs, many=True).data, status=status.HTTP_200_OK)


class ConciergeRequestListCreateView(APIView):
    permission_classes = [IsMobileCustomer]

    def get(self, request, *args, **kwargs):
        qs = ConciergeRequest.objects.filter(customer=request.user.mobile_customer)
        return Response(ConciergeRequestSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = ConciergeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = serializer.validated_data["service"]
        obj = ConciergeRequest.objects.create(
            customer=request.user.mobile_customer,
            service=service,
            property_profile=serializer.validated_data.get("property_profile"),
            requested_for_date=serializer.validated_data.get("requested_for_date"),
            notes=serializer.validated_data.get("notes", ""),
            quote_amount=service.base_price,
        )
        return Response(ConciergeRequestSerializer(obj).data, status=status.HTTP_201_CREATED)
