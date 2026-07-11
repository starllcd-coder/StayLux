from django.db import models

from core.models import TimeStampedModel
from mobile_api.auth.models import MobileCustomer
from settings_app.models import PropertyProfile


class ChatConversation(TimeStampedModel):
    title = models.CharField(max_length=200, blank=True, default="")
    related_property = models.ForeignKey(
        PropertyProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_conversations",
    )
    participants = models.ManyToManyField(MobileCustomer, related_name="chat_conversations")

    class Meta:
        ordering = ["-updated_at"]


class ChatMessage(TimeStampedModel):
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(MobileCustomer, on_delete=models.CASCADE, related_name="chat_messages")
    body = models.TextField()
    translated_body = models.TextField(blank=True, default="")
    attachment_url = models.CharField(max_length=500, blank=True, default="")
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
