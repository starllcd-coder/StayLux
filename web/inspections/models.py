from __future__ import annotations

from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError

from core.models import TimeStampedModel
from settings_app.models import PropertyProfile
from contracts.models import Contract


class InspectionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    COMPLETED = "completed", "Completed"


class MoveOutInspection(TimeStampedModel):
    """
    One move-out inspection per contract (Phase A).
    Stores deductions and computes refundable deposit.
    """
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="moveout_inspections")
    contract = models.OneToOneField(Contract, on_delete=models.CASCADE, related_name="moveout_inspection")

    status = models.CharField(max_length=20, choices=InspectionStatus.choices, default=InspectionStatus.DRAFT)

    inspection_date = models.DateField(null=True, blank=True)

    # Checklist flags (simple)
    keys_returned = models.BooleanField(default=False)
    unit_clean = models.BooleanField(default=False)
    no_damage = models.BooleanField(default=False)

    # Financials
    deductions = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    notes = models.TextField(blank=True, default="")

    # Computed snapshot at completion time
    refundable_amount = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property_profile", "status"]),
        ]

    def __str__(self) -> str:
        return f"MoveOutInspection #{self.id} (Contract {self.contract_id})"

    def clean(self):
        if self.contract.property_profile_id != self.property_profile_id:
            raise ValidationError("contract property_profile does not match inspection property_profile")
        if self.deductions < Decimal("0.000"):
            raise ValidationError("deductions cannot be negative")