from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from housekeeping.models import HousekeepingTask
from maintenance.models import MaintenanceRequest
from .models import StaffJobNotification
from django.db import transaction
from .push import dispatch_notification_safely


@receiver(pre_save, sender=HousekeepingTask)
@receiver(pre_save, sender=MaintenanceRequest)
def remember_assignment(sender, instance, raw=False, **kwargs):
    if raw:
        return
    instance._previous_assignee = sender.objects.filter(pk=instance.pk).values_list("assigned_to_id", flat=True).first() if instance.pk else None


@receiver(post_save, sender=HousekeepingTask)
@receiver(post_save, sender=MaintenanceRequest)
def notify_assigned_staff(sender, instance, raw=False, update_fields=None, **kwargs):
    if raw or (update_fields is not None and "assigned_to" not in update_fields and "assigned_to_id" not in update_fields):
        return
    if not instance.assigned_to_id or instance.assigned_to_id == getattr(instance, "_previous_assignee", None):
        return
    staff = instance.assigned_to
    if not staff.is_active or not staff.user.is_active or staff.property_id != instance.property_profile_id:
        return
    housekeeping = sender is HousekeepingTask
    if staff.role not in {"housekeeping" if housekeeping else "maintenance", "manager", "owner_admin"}:
        return
    if instance.status in {"done", "resolved", "cancelled"}:
        return
    notification = StaffJobNotification.objects.create(
        recipient=staff,
        housekeeping_task=instance if housekeeping else None,
        maintenance_request=None if housekeeping else instance,
        title="Housekeeping job assigned" if housekeeping else "Maintenance job assigned",
        message=f"{instance.unit.code}: {instance.title} (Priority: {instance.priority})",
    )
    transaction.on_commit(lambda: dispatch_notification_safely(notification.pk))
