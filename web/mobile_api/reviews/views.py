from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from mobile_api.permissions import IsMobileCustomer
from mobile_api.reviews.models import PropertyReview
from mobile_api.reviews.serializers import (
    PropertyReviewSerializer,
    PropertyReviewCreateSerializer,
)


class PropertyReviewListView(ListAPIView):
    serializer_class = PropertyReviewSerializer
    permission_classes = [IsMobileCustomer]

    def get_queryset(self):
        property_id = self.kwargs["property_id"]
        return PropertyReview.objects.filter(
            property_profile_id=property_id,
            is_visible=True,
        ).order_by("-created_at")


class PropertyReviewCreateView(APIView):
    permission_classes = [IsMobileCustomer]

    def post(self, request):

        serializer = PropertyReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review = serializer.save(
            customer=request.user.mobile_customer
        )

        return Response(
            PropertyReviewSerializer(review).data,
            status=status.HTTP_201_CREATED,
        )