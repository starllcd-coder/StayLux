from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from mobile_api.permissions import IsMobileCustomer
from mobile_api.profile.models import MobilePaymentMethod, TravelerProfile
from mobile_api.profile.serializers import (
    CustomerProfileDetailSerializer,
    MobilePaymentMethodCreateSerializer,
    MobilePaymentMethodSerializer,
    NotificationSettingsSerializer,
    TravelerProfileCreateUpdateSerializer,
    TravelerProfileSerializer,
)


class CustomerProfileView(APIView):
    permission_classes = [IsMobileCustomer]

    def get(self, request, *args, **kwargs):
        customer = request.user.mobile_customer
        payload = {
            "customer": customer,
            "travelers": customer.travelers.filter(is_active=True).order_by("-is_default", "-created_at"),
            "payment_methods": customer.payment_methods.filter(is_active=True).order_by("-is_default", "-created_at"),
        }
        serializer = CustomerProfileDetailSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TravelerProfileListCreateView(ListCreateAPIView):
    permission_classes = [IsMobileCustomer]

    def get_queryset(self):
        return TravelerProfile.objects.filter(
            customer=self.request.user.mobile_customer,
            is_active=True,
        ).order_by("-is_default", "-created_at")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TravelerProfileCreateUpdateSerializer
        return TravelerProfileSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = TravelerProfileSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user.mobile_customer)

    def create(self, request, *args, **kwargs):
        serializer = TravelerProfileCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        traveler = serializer.save(customer=request.user.mobile_customer)
        response_serializer = TravelerProfileSerializer(traveler)
        return Response(
            {
                "message": "Traveler profile created successfully.",
                "traveler": response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class TravelerProfileDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsMobileCustomer]
    lookup_field = "pk"

    def get_queryset(self):
        return TravelerProfile.objects.filter(customer=self.request.user.mobile_customer)

    def get_serializer_class(self):
        if self.request.method in ["PATCH", "PUT"]:
            return TravelerProfileCreateUpdateSerializer
        return TravelerProfileSerializer

    def retrieve(self, request, *args, **kwargs):
        traveler = self.get_object()
        serializer = TravelerProfileSerializer(traveler)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        traveler = self.get_object()
        serializer = TravelerProfileCreateUpdateSerializer(
            traveler,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        traveler = serializer.save()
        response_serializer = TravelerProfileSerializer(traveler)
        return Response(
            {
                "message": "Traveler profile updated successfully.",
                "traveler": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        traveler = self.get_object()
        traveler.is_active = False
        traveler.save(update_fields=["is_active", "updated_at"])
        return Response(
            {"message": "Traveler profile removed successfully."},
            status=status.HTTP_200_OK,
        )


class PaymentMethodListCreateView(APIView):
    permission_classes = [IsMobileCustomer]

    def get(self, request, *args, **kwargs):
        qs = MobilePaymentMethod.objects.filter(
            customer=request.user.mobile_customer,
            is_active=True,
        ).order_by("-is_default", "-created_at")
        return Response(MobilePaymentMethodSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = MobilePaymentMethodCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save(customer=request.user.mobile_customer, is_active=True)
        return Response(
            {
                "message": "Payment method added.",
                "payment_method": MobilePaymentMethodSerializer(obj).data,
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentMethodDetailView(APIView):
    permission_classes = [IsMobileCustomer]

    def delete(self, request, id, *args, **kwargs):
        obj = MobilePaymentMethod.objects.filter(
            id=id,
            customer=request.user.mobile_customer,
            is_active=True,
        ).first()
        if not obj:
            raise NotFound("Payment method not found.")
        obj.is_active = False
        obj.save(update_fields=["is_active", "updated_at"])
        return Response({"message": "Payment method removed."}, status=status.HTTP_200_OK)


class PaymentMethodSetDefaultView(APIView):
    permission_classes = [IsMobileCustomer]

    def post(self, request, id, *args, **kwargs):
        obj = MobilePaymentMethod.objects.filter(
            id=id,
            customer=request.user.mobile_customer,
            is_active=True,
        ).first()
        if not obj:
            raise NotFound("Payment method not found.")
        obj.is_default = True
        obj.save(update_fields=["is_default", "updated_at"])
        return Response(
            {"message": "Default payment method updated.", "payment_method": MobilePaymentMethodSerializer(obj).data},
            status=status.HTTP_200_OK,
        )


class NotificationSettingsView(APIView):
    permission_classes = [IsMobileCustomer]

    def get(self, request, *args, **kwargs):
        customer = request.user.mobile_customer
        serializer = NotificationSettingsSerializer(customer)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        customer = request.user.mobile_customer
        serializer = NotificationSettingsSerializer(customer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
