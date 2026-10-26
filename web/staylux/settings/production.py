from .base import *
import os
from django.core.exceptions import ImproperlyConfigured


def get_env(name: str, required: bool = True):
    value = os.environ.get(name)
    if required and not value:
        raise ImproperlyConfigured(
            f"Missing required environment variable: {name}"
        )
    return value


# Production secrets must be provided by the hosting platform.
SECRET_KEY = get_env("DJANGO_SECRET_KEY")
DEBUG = False

ALLOWED_HOSTS = [
    host.strip()
    for host in get_env("DJANGO_ALLOWED_HOSTS").split(",")
    if host.strip()
]

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must contain at least one hostname"
    )

# Railway PostgreSQL connection settings.
DB_ENGINE = get_env("DB_ENGINE")
if DB_ENGINE != "django.db.backends.postgresql":
    raise ImproperlyConfigured(
        "Production DB_ENGINE must be django.db.backends.postgresql"
    )

DATABASES = {
    "default": {
        "ENGINE": DB_ENGINE,
        "NAME": get_env("DB_NAME"),
        "USER": get_env("DB_USER"),
        "PASSWORD": get_env("DB_PASSWORD"),
        "HOST": get_env("DB_HOST"),
        "PORT": get_env("DB_PORT"),
        "CONN_MAX_AGE": 60,
    }
}

# Railway terminates HTTPS at its proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = (
    os.environ.get("SECURE_SSL_REDIRECT", "1") == "1"
)

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

CSRF_TRUSTED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.environ.get(
        "CSRF_TRUSTED_ORIGINS", ""
    ).split(",")
    if origin.strip()
]

SECURE_HSTS_SECONDS = int(
    os.environ.get("SECURE_HSTS_SECONDS", "3600")
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True