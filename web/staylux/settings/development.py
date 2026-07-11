from .base import *
import os

# Development-friendly defaults
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Keep SQLite as the default local DB for development
DATABASES = {
    "default": {
        # If an environment variable exists but is empty, fall back to SQLite.
        "ENGINE": os.environ.get("DB_ENGINE") or "django.db.backends.sqlite3",
        "NAME": os.environ.get("DB_NAME") or str(DATA_DIR / "db.sqlite3"),
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", ""),
        "PORT": os.environ.get("DB_PORT", ""),
    }
}
