from rest_framework import serializers
from .models import NotificationSetting, WhatsAppTemplate, OutboxMessage


class NotificationSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSetting
        fields = [
            "id",
            "property_profile",
            "enable_whatsapp",
            "default_channel",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")


class WhatsAppTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsAppTemplate
        fields = [
            "id",
            "property_profile",
            "key",
            "language",
            "body",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")


class OutboxMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutboxMessage
        fields = [
            "id",
            "property_profile",
            "channel",
            "to_phone",
            "to_email",
            "event_key",
            "language",
            "content",
            "status",
            "provider_message_id",
            "error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")