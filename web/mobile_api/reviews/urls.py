from django.urls import path

from mobile_api.reviews.views import (
    PropertyReviewListView,
    PropertyReviewCreateView,
)

app_name = "mobile_reviews"

urlpatterns = [
    path("property/<int:property_id>/", PropertyReviewListView.as_view()),
    path("create/", PropertyReviewCreateView.as_view()),
]