from django.urls import path

from mobile_api.discovery.views import (
    DiscoveryHealthView,
    FeaturedPropertyListView,
    PropertyDetailView,
    PropertyListView,
    PropertySearchView,
    PropertySearchSuggestionView,
    SimilarPropertyListView,
    PropertyUnitListView,
    RecommendedPropertyListView,
)

app_name = "mobile_discovery"

urlpatterns = [
    path("health/", DiscoveryHealthView.as_view(), name="health"),
    path("properties/", PropertyListView.as_view(), name="property-list"),
    path("properties/featured/", FeaturedPropertyListView.as_view(), name="property-featured"),
    path("properties/recommended/", RecommendedPropertyListView.as_view(), name="property-recommended"),
    path("properties/search/", PropertySearchView.as_view(), name="property-search"),
    path("properties/suggestions/", PropertySearchSuggestionView.as_view(), name="property-suggestions"),
    path("properties/<int:id>/", PropertyDetailView.as_view(), name="property-detail"),
    path("properties/<int:id>/similar/", SimilarPropertyListView.as_view(), name="property-similar"),
    path("properties/<int:id>/units/", PropertyUnitListView.as_view(), name="property-units"),
]
