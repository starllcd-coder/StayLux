from __future__ import annotations

from django.db import transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from sync_engine.services import record_sync_event, serialize_instance, should_capture_model


@receiver(post_save)
def sync_capture_save(sender, instance, created, **kwargs):
    if getattr(sender._meta, "app_label", "") == "sync_engine":
        return
    model_label = sender._meta.label_lower
    if not should_capture_model(model_label):
        return
    operation = "create" if created else "update"
    # Never write sync rows inside the caller's atomic transaction.
    # If sync persistence fails, it must not poison booking/payment transactions.
    transaction.on_commit(lambda: record_sync_event(instance=instance, operation=operation))


@receiver(pre_delete)
def sync_capture_delete(sender, instance, **kwargs):
    if getattr(sender._meta, "app_label", "") == "sync_engine":
        return
    model_label = sender._meta.label_lower
    if not should_capture_model(model_label):
        return
    payload = serialize_instance(instance)
    transaction.on_commit(
        lambda: record_sync_event(instance=instance, operation="delete", payload=payload)
    )
