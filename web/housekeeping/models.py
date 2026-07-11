from django.db import models
from core.models import TimeStampedModel
from settings_app.models import PropertyProfile
from inventory.models import Unit
from bookings.models import Booking
from accounts.models import StaffProfile


class HousekeepingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    DONE = "done", "Done"
    CANCELLED = "cancelled", "Cancelled"


class HousekeepingTask(TimeStampedModel):
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="housekeeping_tasks")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="housekeeping_tasks")
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name="housekeeping_tasks")

    assigned_to = models.ForeignKey(
        StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="housekeeping_tasks"
    )

    status = models.CharField(max_length=20, choices=HousekeepingStatus.choices, default=HousekeepingStatus.PENDING)
    priority = models.CharField(max_length=20, default="normal")  # normal / high

    title = models.CharField(max_length=200, default="Housekeeping task")
    notes = models.TextField(blank=True, default="")

    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property_profile", "status"]),
            models.Index(fields=["unit", "status"]),
        ]

    def __str__(self):
        return f"{self.unit.code} - {self.status}"