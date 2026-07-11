from django.contrib import admin
from django.urls import include, path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from api.auth_views import RecoveryContactView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),

    # Existing JWT auth endpoints
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/recovery-contact/", RecoveryContactView.as_view(), name="recovery_contact"),

    # Existing admin/web API
    path("api/", include("api.urls")),

    # New mobile API
    path("api/mobile/", include("mobile_api.urls")),

    # Web UI (Django templates)
    path("", include("core.urls")),

    # Owner portal
    path("owner/", include("owner_portal.urls")),
]
