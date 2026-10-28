from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import NotificationSetting, WhatsAppTemplate, OutboxMessage
from .serializers import NotificationSettingSerializer, WhatsAppTemplateSerializer, OutboxMessageSerializer
from .models import StaffJobNotification
from .models import StaffPushDevice
from rest_framework.exceptions import PermissionDenied


class StaffJobNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffJobNotification
        fields = ["id", "title", "message", "is_read", "created_at", "housekeeping_task", "maintenance_request"]
        read_only_fields = fields


class StaffJobNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StaffJobNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = StaffJobNotification.objects.filter(
            recipient__user=self.request.user, recipient__is_active=True,
            recipient__user__is_active=True,
        )
        if self.request.query_params.get("unread") == "1":
            qs = qs.filter(is_read=False)
        return qs

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read", "updated_at"])
        return Response(self.get_serializer(notification).data)


class StaffPushDeviceSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512, min_length=20, write_only=True)
    platform = serializers.ChoiceField(choices=["android", "ios"])


class StaffPushDeviceViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = StaffPushDeviceSerializer

    def _staff(self):
        staff = getattr(self.request.user, "staff_profile", None)
        if not staff or not staff.is_active or not self.request.user.is_active:
            raise PermissionDenied("An active staff profile is required")
        return staff

    def create(self, request):
        staff = self._staff()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        StaffPushDevice.objects.update_or_create(
            token=serializer.validated_data["token"],
            defaults={"recipient": staff, "platform": serializer.validated_data["platform"], "is_active": True},
        )
        return Response({"registered": True})

    @action(detail=False, methods=["post"])
    def unregister(self, request):
        staff = self._staff()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        StaffPushDevice.objects.filter(recipient=staff, token=serializer.validated_data["token"]).update(is_active=False)
        return Response({"registered": False})


class NotificationSettingViewSet(viewsets.ModelViewSet):
    queryset = NotificationSetting.objects.select_related("property_profile").all()
    serializer_class = NotificationSettingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        prop = self.request.query_params.get("property_profile")
        if prop:
            qs = qs.filter(property_profile_id=prop)
        return qs


class WhatsAppTemplateViewSet(viewsets.ModelViewSet):
    queryset = WhatsAppTemplate.objects.select_related("property_profile").all()
    serializer_class = WhatsAppTemplateSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        prop = self.request.query_params.get("property_profile")
        if prop:
            qs = qs.filter(property_profile_id=prop)
        key = self.request.query_params.get("key")
        if key:
            qs = qs.filter(key=key)
        lang = self.request.query_params.get("language")
        if lang:
            qs = qs.filter(language=lang)
        return qs


class OutboxMessageViewSet(viewsets.ModelViewSet):
    queryset = OutboxMessage.objects.select_related("property_profile").all()
    serializer_class = OutboxMessageSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        prop = self.request.query_params.get("property_profile")
        if prop:
            qs = qs.filter(property_profile_id=prop)
        status_q = self.request.query_params.get("status")
        if status_q:
            qs = qs.filter(status=status_q)
        event_key = self.request.query_params.get("event_key")
        if event_key:
            qs = qs.filter(event_key=event_key)
        return qs
