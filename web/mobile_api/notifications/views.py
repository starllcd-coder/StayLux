from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from mobile_api.permissions import IsMobileCustomer
from mobile_api.notifications.models import MobileNotification
from mobile_api.notifications.serializers import NotificationSerializer

try:
    from mobile_api.notifications.models import MobileDevice
except Exception:  # pragma: no cover - startup guard for partial deployments
    MobileDevice = None


class NotificationListView(ListAPIView):
    permission_classes = [IsMobileCustomer]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return MobileNotification.objects.filter(
            customer=self.request.user.mobile_customer
        ).order_by("-created_at")


class NotificationMarkReadView(APIView):
    permission_classes = [IsMobileCustomer]

    def post(self, request, id):
        notification = MobileNotification.objects.filter(
            id=id,
            customer=request.user.mobile_customer
        ).first()

        if not notification:
            return Response({"error": "Notification not found"}, status=404)

        notification.is_read = True
        notification.save(update_fields=["is_read", "updated_at"])

        return Response({"success": True})


class DeviceRegisterView(APIView):
    permission_classes = [IsMobileCustomer]

    def post(self, request):
        if MobileDevice is None:
            return Response(
                {"detail": "Device registration is temporarily unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        token = (request.data.get("device_token") or "").strip()
        platform = (request.data.get("platform") or "").strip().lower()

        if not token:
            return Response({"device_token": "Device token is required."}, status=status.HTTP_400_BAD_REQUEST)

        obj, _ = MobileDevice.objects.update_or_create(
            device_token=token,
            defaults={
                "customer": request.user.mobile_customer,
                "platform": platform,
            },
        )
        return Response(
            {
                "id": obj.id,
                "device_token": obj.device_token,
                "platform": obj.platform,
                "message": "Device registered for notifications.",
            },
            status=status.HTTP_200_OK,
        )
