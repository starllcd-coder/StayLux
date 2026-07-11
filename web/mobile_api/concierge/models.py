from django.db import models

from core.models import TimeStampedModel
from mobile_api.auth.models import MobileCustomer
from settings_app.models import PropertyProfile


class ConciergeService(TimeStampedModel):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    base_price = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]


class ConciergeRequest(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    customer = models.ForeignKey(MobileCustomer, on_delete=models.CASCADE, related_name="concierge_requests")
    service = models.ForeignKey(ConciergeService, on_delete=models.PROTECT, related_name="requests")
    property_profile = models.ForeignKey(
        PropertyProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="concierge_requests",
    )
    requested_for_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    quote_amount = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    class Meta:
        ordering = ["-created_at"]
