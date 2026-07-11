from django.db import models

from core.models import TimeStampedModel
from mobile_api.auth.models import MobileCustomer


class MobileNotification(TimeStampedModel):

    customer = models.ForeignKey(
        MobileCustomer,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    title = models.CharField(max_length=255)
    message = models.TextField()

    is_read = models.BooleanField(default=False)


class MobileDevice(TimeStampedModel):
    """Represents a registered mobile device for push notifications.

    Fields are intentionally minimal to satisfy the API serializer used
    by the mobile client: `device_token` and `platform`.
    """

    customer = models.ForeignKey(
        MobileCustomer,
        on_delete=models.CASCADE,
        related_name="devices",
        null=True,
        blank=True,
    )

    device_token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.platform}:{self.device_token[:8]}"