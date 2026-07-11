from django.db import models

from core.models import TimeStampedModel
from mobile_api.auth.models import MobileCustomer
from settings_app.models import PropertyProfile


class PropertyReview(TimeStampedModel):
    customer = models.ForeignKey(
        MobileCustomer,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    property_profile = models.ForeignKey(
        PropertyProfile,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    rating = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200, blank=True, default="")
    comment = models.TextField(blank=True, default="")
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property_profile"]),
            models.Index(fields=["customer"]),
        ]

    def __str__(self):
        return f"{self.customer.full_name} - {self.rating}"