from rest_framework import serializers

from mobile_api.chat.models import ChatConversation, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.full_name", read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "conversation",
            "sender",
            "sender_name",
            "body",
            "translated_body",
            "attachment_url",
            "is_system",
            "created_at",
        ]
        read_only_fields = ["sender", "is_system", "translated_body", "created_at"]


class ChatConversationSerializer(serializers.ModelSerializer):
    participant_ids = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatConversation
        fields = [
            "id",
            "title",
            "related_property",
            "participant_ids",
            "last_message",
            "created_at",
            "updated_at",
        ]

    def get_participant_ids(self, obj):
        return list(obj.participants.values_list("id", flat=True))

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        if not msg:
            return None
        return {"id": msg.id, "body": msg.body[:120], "created_at": msg.created_at}
