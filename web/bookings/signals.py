from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from inventory.models import UnitStatus, Unit
from .models import Booking, BookingStatus

# ✅ NEW import
from housekeeping.models import HousekeepingTask, HousekeepingStatus


@receiver(pre_save, sender=Booking)
def capture_previous_booking_status(sender, instance: Booking, **kwargs):
    """
    Store the previous status on the instance so post_save can detect transitions.
    """
    instance._prev_status = None
    if instance.pk:
        try:
            prev = Booking.objects.only("status").get(pk=instance.pk)
            instance._prev_status = prev.status
        except Booking.DoesNotExist:
            instance._prev_status = None


@receiver(post_save, sender=Booking)
def on_booking_saved(sender, instance: Booking, created: bool, **kwargs):
    unit: Unit = instance.unit
    prev_status = getattr(instance, "_prev_status", None)

    # ✅ Unit status sync (phase A)
    if instance.status == BookingStatus.CHECKED_IN:
        if unit.status != UnitStatus.OCCUPIED:
            Unit.objects.filter(id=unit.id).update(status=UnitStatus.OCCUPIED)

    elif instance.status == BookingStatus.CHECKED_OUT:
        # When checked out, room goes to housekeeping
        if unit.status != UnitStatus.HOUSEKEEPING:
            Unit.objects.filter(id=unit.id).update(status=UnitStatus.HOUSEKEEPING)

        # ✅ Create housekeeping task only on transition into CHECKED_OUT
        if prev_status != BookingStatus.CHECKED_OUT:
            HousekeepingTask.objects.create(
                property_profile=instance.property_profile,
                unit=instance.unit,
                booking=instance,
                status=HousekeepingStatus.PENDING,
                priority="normal",
                title=f"Clean after checkout: {instance.unit.code}",
                notes=f"Auto-created on checkout for booking #{instance.id}.",
            )

    elif instance.status in [BookingStatus.CANCELLED, BookingStatus.NO_SHOW]:
        # For cancelled/no-show we don't change unit status automatically here
        pass