from .base import *
import os
from django.core.exceptions import ImproperlyConfigured


def get_env(name: str, required: bool = True):
    v = os.environ.get(name)
    if required and not v:
        raise ImproperlyConfigured(f"Missing required environment variable: {name}")
    return v


# Production must explicitly set SECRET_KEY and ALLOWED_HOSTS
SECRET_KEY = get_env("DJANGO_SECRET_KEY", required=True)
DEBUG = False
ALLOWED_HOSTS = get_env("DJANGO_ALLOWED_HOSTS", required=True).split(",")

# Database configuration must be provided via environment in production
DB_ENGINE = os.environ.get("DB_ENGINE")
if not DB_ENGINE:
    raise ImproperlyConfigured("Missing DB_ENGINE for production")

DATABASES = {
    "default": {
        "ENGINE": DB_ENGINE,
        "NAME": get_env("DB_NAME"),
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", ""),
        "PORT": os.environ.get("DB_PORT", ""),
    }
}

# Security hardening defaults for production
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "1") == "1"
