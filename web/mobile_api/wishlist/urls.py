from django.urls import path

from mobile_api.wishlist.views import (
    WishlistCollectionListCreateView,
    WishlistCollectionShareView,
    WishlistListView,
    WishlistPriceAlertView,
    WishlistSharedCollectionView,
    WishlistToggleView,
)

app_name = "mobile_wishlist"

urlpatterns = [
    path("", WishlistListView.as_view()),
    path("toggle/", WishlistToggleView.as_view()),
    path("collections/", WishlistCollectionListCreateView.as_view()),
    path("collections/<int:id>/share/", WishlistCollectionShareView.as_view()),
    path("shared/<str:token>/", WishlistSharedCollectionView.as_view()),
    path("<int:id>/price-alert/", WishlistPriceAlertView.as_view()),
]
