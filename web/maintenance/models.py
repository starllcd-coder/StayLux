from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.models import TimeStampedModel
from settings_app.models import PropertyProfile
from inventory.models import Unit
from accounts.models import StaffProfile


class MaintenanceStatus(models.TextChoices):
    OPEN = "open", _("Open")
    IN_PROGRESS = "in_progress", _("In Progress")
    RESOLVED = "resolved", _("Resolved")
    CANCELLED = "cancelled", _("Cancelled")


class MaintenancePriority(models.TextChoices):
    LOW = "low", _("Low")
    NORMAL = "normal", _("Normal")
    HIGH = "high", _("High")
    URGENT = "urgent", _("Urgent")


class MaintenanceType(models.TextChoices):
    ELECTRICAL = "electrical", _("Electrical")
    PLUMBING = "plumbing", _("Plumbing")
    HVAC = "hvac", _("HVAC")
    APPLIANCE = "appliance", _("Appliance")
    CARPENTRY = "carpentry", _("Carpentry")
    PAINTING = "painting", _("Painting")
    CLEANING = "cleaning", _("Deep Cleaning")
    GENERAL = "general", _("General")


class MaintenanceRequest(TimeStampedModel):
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="maintenance_requests")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="maintenance_requests")

    reported_by = models.ForeignKey(
        StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_reported"
    )
    assigned_to = models.ForeignKey(
        StaffProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="maintenance_assigned"
    )

    status = models.CharField(max_length=20, choices=MaintenanceStatus.choices, default=MaintenanceStatus.OPEN)
    priority = models.CharField(max_length=20, choices=MaintenancePriority.choices, default=MaintenancePriority.NORMAL)
    maintenance_type = models.CharField(max_length=30, choices=MaintenanceType.choices, default=MaintenanceType.GENERAL)

    title = models.CharField(max_length=200, default=_("Maintenance request"))
    description = models.TextField(blank=True, default="")

    before_photo = models.ImageField(upload_to="maintenance/before/", blank=True, null=True)
    after_photo = models.ImageField(upload_to="maintenance/after/", blank=True, null=True)

    material_cost = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    labor_cost = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    completed_notes = models.TextField(blank=True, default="")
    completed_at = models.DateTimeField(null=True, blank=True)

    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property_profile", "status"]),
            models.Index(fields=["unit", "status"]),
        ]

    def __str__(self):
        return f"{self.unit.code} - {self.status}"

    def mark_resolved(self):
        self.status = MaintenanceStatus.RESOLVED
        self.resolved_at = timezone.now()