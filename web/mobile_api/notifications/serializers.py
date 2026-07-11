from rest_framework import serializers

from mobile_api.notifications.models import MobileNotification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileNotification
        fields = [
            "id",
            "title",
            "message",
            "is_read",
            "created_at",
        ]
