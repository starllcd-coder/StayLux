from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedModel
from settings_app.models import PropertyProfile, BusinessType


class IDType(models.TextChoices):
    NATIONAL_ID = "national_id", _("National ID")
    PASSPORT = "passport", _("Passport")
    DRIVING_LICENSE = "driving_license", _("License")


class Guest(TimeStampedModel):
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="guests")
    business_type = models.CharField(max_length=20, choices=BusinessType.choices, default=BusinessType.HOTEL)

    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=50, blank=True, default="")
    whatsapp = models.CharField(max_length=50, blank=True, default="")
    email = models.EmailField(blank=True, default="")

    nationality = models.CharField(max_length=100, blank=True, default="")
    id_type = models.CharField(max_length=20, choices=IDType.choices, default=IDType.PASSPORT)
    id_number = models.CharField(max_length=100, blank=True, default="")
    id_expiry = models.DateField(blank=True, null=True)
    id_document = models.FileField(upload_to="guests/id_docs/", blank=True, null=True)

    address = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property_profile", "full_name"]),
            models.Index(fields=["property_profile", "phone"]),
            models.Index(fields=["property_profile", "id_number"]),
            models.Index(fields=["property_profile", "business_type"]),
        ]

    def __str__(self):
        return self.full_name