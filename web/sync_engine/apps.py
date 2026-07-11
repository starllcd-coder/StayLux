from django.apps import AppConfig


class SyncEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sync_engine"

    def ready(self):
        # Register signal handlers for offline-first event journaling.
        from . import signals  # noqa: F401
