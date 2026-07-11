import logging

from django.urls import include, path

logger = logging.getLogger(__name__)
app_name = "mobile_api"

urlpatterns = [
    path("auth/", include("mobile_api.auth.urls")),
    path("profile/", include("mobile_api.profile.urls")),
    path("discovery/", include("mobile_api.discovery.urls")),
    path("bookings/", include("mobile_api.bookings.urls")),
    path("chat/", include("mobile_api.chat.urls")),
    path("concierge/", include("mobile_api.concierge.urls")),
    path("growth/", include("mobile_api.growth.urls")),
    path("reviews/", include("mobile_api.reviews.urls")),
    path("wishlist/", include("mobile_api.wishlist.urls")),
]

try:
    urlpatterns.append(path("notifications/", include("mobile_api.notifications.urls")))
except Exception:  # pragma: no cover - avoid blocking auth routes due optional module issues
    logger.exception("mobile_api.notifications.urls failed to load; skipping notifications routes.")
