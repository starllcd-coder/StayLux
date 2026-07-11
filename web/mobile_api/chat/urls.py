from django.urls import path

from mobile_api.chat.views import ChatTemplatesView, ConversationListCreateView, ConversationMessagesView

app_name = "mobile_chat"

urlpatterns = [
    path("conversations/", ConversationListCreateView.as_view(), name="conversation-list-create"),
    path("conversations/<int:id>/messages/", ConversationMessagesView.as_view(), name="conversation-messages"),
    path("templates/", ChatTemplatesView.as_view(), name="chat-templates"),
]
