from django.urls import path

from mobile_api.concierge.views import ConciergeRequestListCreateView, ConciergeServiceListView

app_name = "mobile_concierge"

urlpatterns = [
    path("services/", ConciergeServiceListView.as_view(), name="concierge-services"),
    path("requests/", ConciergeRequestListCreateView.as_view(), name="concierge-requests"),
]
