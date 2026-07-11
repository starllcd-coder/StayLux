from django.db import models

from core.models import TimeStampedModel
from guests.models import IDType
from mobile_api.auth.models import MobileCustomer


class TravelerProfile(TimeStampedModel):
    customer = models.ForeignKey(
        MobileCustomer,
        on_delete=models.CASCADE,
        related_name="travelers",
    )
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=50, blank=True, default="")
    whatsapp = models.CharField(max_length=50, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    nationality = models.CharField(max_length=100, blank=True, default="")
    id_type = models.CharField(
        max_length=20,
        choices=IDType.choices,
        default=IDType.PASSPORT,
    )
    id_number = models.CharField(max_length=100, blank=True, default="")
    id_expiry = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]
        indexes = [
            models.Index(fields=["customer", "is_default"]),
            models.Index(fields=["customer", "is_active"]),
            models.Index(fields=["customer", "full_name"]),
        ]

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            TravelerProfile.objects.filter(customer=self.customer).exclude(pk=self.pk).update(is_default=False)


class MobilePaymentMethod(TimeStampedModel):
    customer = models.ForeignKey(
        MobileCustomer,
        on_delete=models.CASCADE,
        related_name="payment_methods",
    )
    brand = models.CharField(max_length=40)
    last4 = models.CharField(max_length=4)
    exp_month = models.PositiveSmallIntegerField()
    exp_year = models.PositiveSmallIntegerField()
    provider_token = models.CharField(max_length=255, blank=True, default="")
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]
        indexes = [
            models.Index(fields=["customer", "is_default"]),
            models.Index(fields=["customer", "is_active"]),
        ]

    def __str__(self):
        return f"{self.brand} **** {self.last4}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            MobilePaymentMethod.objects.filter(customer=self.customer).exclude(pk=self.pk).update(is_default=False)
