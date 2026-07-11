from django.db.models.signals import post_save
from django.dispatch import receiver

from inventory.models import Unit, UnitStatus
from .models import MaintenanceRequest, MaintenanceStatus


@receiver(post_save, sender=MaintenanceRequest)
def sync_unit_status_from_maintenance(sender, instance: MaintenanceRequest, **kwargs):
    """
    Basic Phase A behavior:
    - OPEN / IN_PROGRESS -> Unit becomes MAINTENANCE
    - RESOLVED -> Unit becomes AVAILABLE (later we can decide housekeeping based on workflow)
    - CANCELLED -> no forced change
    """
    if instance.status in [MaintenanceStatus.OPEN, MaintenanceStatus.IN_PROGRESS]:
        Unit.objects.filter(id=instance.unit_id).update(status=UnitStatus.MAINTENANCE)

    elif instance.status == MaintenanceStatus.RESOLVED:
        Unit.objects.filter(id=instance.unit_id).update(status=UnitStatus.AVAILABLE)