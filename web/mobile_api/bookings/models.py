from django.db import models

from core.models import TimeStampedModel
from mobile_api.auth.models import MobileCustomer


class MobilePaymentRecord(TimeStampedModel):
    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        REQUIRES_ACTION = "requires_action", "Requires Action"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    customer = models.ForeignKey(
        MobileCustomer,
        on_delete=models.CASCADE,
        related_name="payment_records",
    )
    booking_id = models.PositiveIntegerField(blank=True, null=True)
    provider = models.CharField(max_length=50, blank=True, default="")
    provider_reference = models.CharField(max_length=255, blank=True, default="")
    currency = models.CharField(max_length=10, default="OMR")
    amount = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    payment_method = models.CharField(max_length=50, blank=True, default="")
    client_secret = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["booking_id"]),
            models.Index(fields=["provider_reference"]),
        ]

    def __str__(self):
        return f"{self.customer.full_name} - {self.amount} {self.currency} - {self.status}"


class MobileIdempotencyKey(TimeStampedModel):
    key = models.CharField(max_length=128, unique=True)
    customer = models.ForeignKey(
        MobileCustomer,
        on_delete=models.CASCADE,
        related_name="idempotency_keys",
        null=True,
        blank=True,
    )
    booking_id = models.PositiveIntegerField(null=True, blank=True)
    payment_id = models.PositiveIntegerField(null=True, blank=True)
    data = models.JSONField(null=True, blank=True, default=dict)

    class Meta:
        indexes = [models.Index(fields=["key"])]

    def __str__(self):
        return f"Idemp {self.key} ({self.customer})"


class MobilePaymentSecurityCheck(TimeStampedModel):
    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        FAILED = "failed", "Failed"
        REVIEW = "review", "Manual Review"

    payment = models.OneToOneField(
        MobilePaymentRecord,
        on_delete=models.CASCADE,
        related_name="security_check",
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    risk_score = models.PositiveSmallIntegerField(default=0)
    requires_manual_review = models.BooleanField(default=False)
    fraud_flags = models.JSONField(default=list, blank=True)
    verification_notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["verification_status"]),
            models.Index(fields=["risk_score"]),
        ]
