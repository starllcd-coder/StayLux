from __future__ import annotations

import re
from decimal import Decimal
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.models import TimeStampedModel
from django.utils.translation import gettext_lazy as _
from settings_app.models import PropertyProfile
from guests.models import Guest
from bookings.models import Booking, BookingGroup


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ISSUED = "issued", _("Issued")
    PAID = "paid", _("Paid")
    VOID = "void", _("Void")


class PaymentMethod(models.TextChoices):
    CASH = "cash", _("Cash")
    CARD = "card", _("Card")
    BANK = "bank", _("Bank Transfer")
    WALLET = "wallet", _("Wallet")
    OTHER = "other", _("Other")


class PaymentDirection(models.TextChoices):
    IN = "in", _("Money In")
    OUT = "out", _("Money Out (Refund)")


class Invoice(TimeStampedModel):
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="invoices")
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")
    booking_group = models.ForeignKey(BookingGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices")
    guest = models.ForeignKey(Guest, on_delete=models.PROTECT, related_name="invoices")

    invoice_no = models.CharField(max_length=50, blank=True, default="", db_index=True)
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)

    issue_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    currency = models.CharField(max_length=10, default="OMR")

    subtotal = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    discount_total = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    tax_total = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    total = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))

    amount_paid = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    balance_due = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))

    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property_profile", "status"]),
            models.Index(fields=["property_profile", "invoice_no"]),
        ]

    def __str__(self):
        return self.invoice_no or f"Invoice #{self.id}"

    def clean(self):
        if self.booking_id:
            if self.booking.property_profile_id != self.property_profile_id:
                raise ValidationError("Booking property_profile does not match invoice property_profile")
        if self.booking_group_id:
            if self.booking_group.property_profile_id != self.property_profile_id:
                raise ValidationError("Booking group property_profile does not match invoice property_profile")
        if self.guest_id and self.guest.property_profile_id != self.property_profile_id:
            raise ValidationError("Guest property_profile does not match invoice property_profile")

    @staticmethod
    def _month_prefix(prop_id: int, dt) -> str:
        # Example: INV-12-202602-
        return f"INV-{prop_id}-{dt:%Y%m}-"

    @classmethod
    def generate_invoice_no(cls, property_profile_id: int) -> str:
        """
        Generates invoice number like:
          INV-{propertyId}-{YYYYMM}-{####}
        Sequence resets per property per month.
        """
        now = timezone.localtime(timezone.now())
        prefix = cls._month_prefix(property_profile_id, now)

        last = (
            cls.objects.filter(property_profile_id=property_profile_id, invoice_no__startswith=prefix)
            .order_by("-created_at")
            .only("invoice_no")
            .first()
        )

        seq = 1
        if last and last.invoice_no:
            m = re.match(rf"^{re.escape(prefix)}(\d+)$", last.invoice_no)
            if m:
                try:
                    seq = int(m.group(1)) + 1
                except ValueError:
                    seq = 1

        return f"{prefix}{seq:04d}"

    def recalc_totals(self):
        lines = list(self.lines.all())
        subtotal = sum((l.line_total for l in lines), Decimal("0.000"))
        discount_total = sum((l.discount_amount for l in lines), Decimal("0.000"))
        tax_total = sum((l.tax_amount for l in lines), Decimal("0.000"))
        total = subtotal - discount_total + tax_total
        if total < Decimal("0.000"):
            total = Decimal("0.000")

        payments = list(self.payments.filter(is_void=False))
        # direction IN adds, OUT subtracts (refund)
        paid_in = sum((p.amount for p in payments if p.direction == PaymentDirection.IN), Decimal("0.000"))
        paid_out = sum((p.amount for p in payments if p.direction == PaymentDirection.OUT), Decimal("0.000"))
        paid_net = paid_in - paid_out

        balance = total - paid_net

        self.subtotal = max(subtotal, Decimal("0.000"))
        self.discount_total = max(discount_total, Decimal("0.000"))
        self.tax_total = max(tax_total, Decimal("0.000"))
        self.total = total
        self.amount_paid = paid_net
        self.balance_due = balance

        # Auto-paid status when fully settled and not VOID
        if self.status != InvoiceStatus.VOID:
            if self.total > Decimal("0.000") and self.balance_due <= Decimal("0.000"):
                self.status = InvoiceStatus.PAID

    @transaction.atomic
    def recalc_and_save(self):
        self.recalc_totals()
        self.save(
            update_fields=[
                "invoice_no",
                "status",
                "subtotal",
                "discount_total",
                "tax_total",
                "total",
                "amount_paid",
                "balance_due",
                "updated_at",
            ]
        )

    @transaction.atomic
    def ensure_invoice_no(self):
        if not self.invoice_no:
            self.invoice_no = Invoice.generate_invoice_no(self.property_profile_id)
            self.save(update_fields=["invoice_no", "updated_at"])


class InvoiceLine(TimeStampedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")

    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("1.000"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))

    discount_amount = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))
    tax_rate = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal("0.000"))  # e.g. 5.000
    tax_amount = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))

    class Meta:
        ordering = ["id"]

    @property
    def line_total(self) -> Decimal:
        return (self.quantity * self.unit_price)

    def recalc_tax(self):
        base = self.line_total - self.discount_amount
        if base < Decimal("0.000"):
            base = Decimal("0.000")
        self.tax_amount = (base * self.tax_rate) / Decimal("100.000")


class Payment(TimeStampedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="payments")

    method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    direction = models.CharField(max_length=10, choices=PaymentDirection.choices, default=PaymentDirection.IN)
    amount = models.DecimalField(max_digits=12, decimal_places=3, default=Decimal("0.000"))

    reference = models.CharField(max_length=120, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)

    is_void = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property_profile", "method"]),
            models.Index(fields=["invoice", "created_at"]),
        ]

    def clean(self):
        if self.invoice.property_profile_id != self.property_profile_id:
            raise ValidationError("Payment property_profile does not match invoice property_profile")
        if self.amount < Decimal("0.000"):
            raise ValidationError("Payment amount must be positive. Use direction=out for refunds.")