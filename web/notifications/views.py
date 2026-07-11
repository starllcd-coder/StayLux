from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import NotificationSetting, WhatsAppTemplate, OutboxMessage
from .serializers import NotificationSettingSerializer, WhatsAppTemplateSerializer, OutboxMessageSerializer


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