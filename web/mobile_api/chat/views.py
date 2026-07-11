from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from mobile_api.chat.models import ChatConversation, ChatMessage
from mobile_api.chat.serializers import ChatConversationSerializer, ChatMessageSerializer
from mobile_api.permissions import IsMobileCustomer


def _auto_translate_stub(text: str) -> str:
    content = (text or "").strip()
    if not content:
        return ""
    # Placeholder until production translation provider is configured.
    return f"[auto-translated] {content}"


class ConversationListCreateView(APIView):
    permission_classes = [IsMobileCustomer]

    def get(self, request, *args, **kwargs):
        customer = request.user.mobile_customer
        qs = ChatConversation.objects.filter(participants=customer).distinct()
        return Response(ChatConversationSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        customer = request.user.mobile_customer
        title = (request.data.get("title") or "").strip()
        related_property = request.data.get("related_property")
        conversation = ChatConversation.objects.create(title=title, related_property_id=related_property or None)
        conversation.participants.add(customer)
        return Response(ChatConversationSerializer(conversation).data, status=status.HTTP_201_CREATED)


class ConversationMessagesView(APIView):
    permission_classes = [IsMobileCustomer]

    def _get_conversation(self):
        conversation_id = self.kwargs["id"]
        customer = self.request.user.mobile_customer
        return ChatConversation.objects.filter(id=conversation_id, participants=customer).first()

    def get(self, request, *args, **kwargs):
        conv = self._get_conversation()
        if not conv:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ChatMessageSerializer(conv.messages.all(), many=True).data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        conv = self._get_conversation()
        if not conv:
            return Response({"detail": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        body = (request.data.get("body") or "").strip()
        if not body:
            return Response({"body": "Message text is required."}, status=status.HTTP_400_BAD_REQUEST)
        msg = ChatMessage.objects.create(
            conversation=conv,
            sender=request.user.mobile_customer,
            body=body,
            translated_body=_auto_translate_stub(body),
            attachment_url=(request.data.get("attachment_url") or "").strip(),
        )
        return Response(ChatMessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class ChatTemplatesView(APIView):
    permission_classes = [IsMobileCustomer]

    def get(self, request, *args, **kwargs):
        templates = [
            "Hello, I need help with my booking.",
            "Can you share check-in instructions?",
            "I want to request airport pickup.",
            "Please confirm my cancellation policy.",
        ]
        return Response({"results": templates}, status=status.HTTP_200_OK)
