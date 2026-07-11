from django.urls import path

from mobile_api.notifications.views import (
    DeviceRegisterView,
    NotificationListView,
    NotificationMarkReadView,
)

app_name = "mobile_notifications"

urlpatterns = [
    path("", NotificationListView.as_view()),
    path("devices/register/", DeviceRegisterView.as_view()),
    path("<int:id>/read/", NotificationMarkReadView.as_view()),
]
