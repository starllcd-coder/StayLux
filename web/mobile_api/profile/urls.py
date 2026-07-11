from django.urls import path

from mobile_api.profile.views import (
    CustomerProfileView,
    NotificationSettingsView,
    PaymentMethodDetailView,
    PaymentMethodListCreateView,
    PaymentMethodSetDefaultView,
    TravelerProfileDetailView,
    TravelerProfileListCreateView,
)

app_name = "mobile_profile"

urlpatterns = [
    path("", CustomerProfileView.as_view(), name="profile"),
    path("notification-settings/", NotificationSettingsView.as_view(), name="notification-settings"),
    path("payment-methods/", PaymentMethodListCreateView.as_view(), name="payment-methods"),
    path("payment-methods/<int:id>/", PaymentMethodDetailView.as_view(), name="payment-method-detail"),
    path("payment-methods/<int:id>/default/", PaymentMethodSetDefaultView.as_view(), name="payment-method-default"),
    path("travelers/", TravelerProfileListCreateView.as_view(), name="traveler-list-create"),
    path("travelers/<int:pk>/", TravelerProfileDetailView.as_view(), name="traveler-detail"),
]
