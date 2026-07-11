from __future__ import annotations

from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

from core.models import TimeStampedModel
from settings_app.models import PropertyProfile
from inventory.models import Unit
from guests.models import Guest
from billing.models import Invoice


class ContractStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ENDED = "ended", "Ended"
    TERMINATED = "terminated", "Terminated"


class DepositStatus(models.TextChoices):
    NOT_REQUIRED = "not_required", "Not Required"
    PENDING = "pending", "Pending"
    RECEIVED = "received", "Received"
    REFUNDED = "refunded", "Refunded"
    PARTIAL_REFUND = "partial_refund", "Partial Refund"


class Contract(TimeStampedModel):
    """
    Monthly apartment contract.
    Includes deposit tracking + termination fields.
    """
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="contracts")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name="contracts")
    guest = models.ForeignKey(Guest, on_delete=models.PROTECT, related_name="contracts")

    status = models.CharField(max_length=20, choices=ContractStatus.choices, default=ContractStatus.DRAFT)

    contract_no = models.CharField(max_length=50, blank=True, default="", db_index=True)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    monthly_rent = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    billing_day = models.PositiveSmallIntegerField(default=1)  # 1..28 recommended
    currency = models.CharField(max_length=10, default="OMR")

    security_deposit = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    deposit_received = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    deposit_refunded = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    deposit_status = models.CharField(max_length=20, choices=DepositStatus.choices, default=DepositStatus.PENDING)

    # Link to deposit invoice (so payments/refunds are recorded in billing)
    deposit_invoice = models.OneToOneField(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="deposit_for_contract"
    )

    # Termination / move-out
    move_out_date = models.DateField(null=True, blank=True)
    termination_reason = models.CharField(max_length=255, blank=True, default="")
    terminated_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True, default="")
    last_invoiced_month = models.CharField(max_length=7, blank=True, default="", db_index=True)  # "YYYY-MM"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property_profile", "status"]),
            models.Index(fields=["property_profile", "unit"]),
            models.Index(fields=["property_profile", "guest"]),
        ]

    def __str__(self):
        return self.contract_no or f"Contract #{self.id}"

    def clean(self):
        if self.unit.property_profile_id != self.property_profile_id:
            raise ValidationError("Unit property_profile does not match contract property_profile")
        if self.guest.property_profile_id != self.property_profile_id:
            raise ValidationError("Guest property_profile does not match contract property_profile")
        if self.billing_day < 1 or self.billing_day > 28:
            raise ValidationError("billing_day must be between 1 and 28 for safety")

    def update_deposit_status(self):
        if self.security_deposit <= Decimal("0.000"):
            self.deposit_status = DepositStatus.NOT_REQUIRED
            return

        if self.deposit_received <= Decimal("0.000"):
            self.deposit_status = DepositStatus.PENDING
            return

        if self.deposit_refunded <= Decimal("0.000"):
            self.deposit_status = DepositStatus.RECEIVED
            return

        if self.deposit_refunded >= self.deposit_received:
            self.deposit_status = DepositStatus.REFUNDED
        else:
            self.deposit_status = DepositStatus.PARTIAL_REFUND

    def mark_deposit_received(self, amount: Decimal):
        self.deposit_received = (self.deposit_received or Decimal("0.000")) + amount
        self.update_deposit_status()
        self.save(update_fields=["deposit_received", "deposit_status", "updated_at"])

    def mark_deposit_refunded(self, amount: Decimal):
        self.deposit_refunded = (self.deposit_refunded or Decimal("0.000")) + amount
        self.update_deposit_status()
        self.save(update_fields=["deposit_refunded", "deposit_status", "updated_at"])

    def mark_ended(self, *, end_date, move_out_date=None, reason: str = "", terminated: bool = False):
        self.end_date = end_date
        self.move_out_date = move_out_date or end_date
        self.termination_reason = reason or ""
        if terminated:
            self.status = ContractStatus.TERMINATED
            self.terminated_at = timezone.now()
        else:
            self.status = ContractStatus.ENDED
            self.terminated_at = None
        self.save(
            update_fields=[
                "end_date",
                "move_out_date",
                "termination_reason",
                "status",
                "terminated_at",
                "updated_at",
            ]
        )


class ContractDocumentType(models.TextChoices):
    SIGNED_AGREEMENT = "signed_agreement", "Signed Agreement"
    TENANT_ID = "tenant_id", "Tenant ID"
    PASSPORT = "passport", "Passport"
    VISA = "visa", "Visa"
    OTHER = "other", "Other"


def contract_document_upload_to(instance: "ContractDocument", filename: str) -> str:
    # media/contracts/<property_id>/<contract_id>/<filename>
    return f"contracts/{instance.property_profile_id}/contract_{instance.contract_id}/{filename}"


class ContractDocument(TimeStampedModel):
    """
    Documents attached to a contract (signed agreement, IDs, etc.)
    """
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="contract_documents")
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="documents")

    doc_type = models.CharField(max_length=30, choices=ContractDocumentType.choices, default=ContractDocumentType.OTHER)
    title = models.CharField(max_length=150, blank=True, default="")
    file = models.FileField(upload_to=contract_document_upload_to)

    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property_profile", "contract"]),
            models.Index(fields=["property_profile", "doc_type"]),
        ]

    def __str__(self) -> str:
        return self.title or f"{self.doc_type} (Contract {self.contract_id})"

    def clean(self):
        if self.contract.property_profile_id != self.property_profile_id:
            raise ValidationError("contract property_profile does not match document property_profile")