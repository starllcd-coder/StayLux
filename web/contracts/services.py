from __future__ import annotations

from decimal import Decimal
from datetime import date
import calendar

from django.utils import timezone
from django.db.models import Q

from billing.models import (
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Payment,
    PaymentDirection,
    PaymentMethod,
)
from .models import Contract, ContractStatus


def month_start(year: int, month: int) -> date:
    return date(year, month, 1)


def month_end(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def compute_prorated_rent(contract: Contract, year: int, month: int) -> Decimal:
    """
    Simple proration:
    - Full month → full rent
    - Partial month → (covered days / total days) * monthly_rent
    """
    m_start = month_start(year, month)
    m_end = month_end(year, month)

    c_start = contract.start_date
    c_end = contract.end_date or date(2099, 12, 31)

    overlap_start = max(m_start, c_start)
    overlap_end = min(m_end, c_end)

    if overlap_end < overlap_start:
        return Decimal("0.000")

    covered_days = (overlap_end - overlap_start).days + 1
    total_days = days_in_month(year, month)

    if covered_days >= total_days:
        return contract.monthly_rent

    ratio = Decimal(covered_days) / Decimal(total_days)
    return (contract.monthly_rent * ratio).quantize(Decimal("0.001"))


def _find_existing_contract_month_invoice(contract: Contract, ym: str) -> Invoice | None:
    """
    Idempotency: 1 invoice per contract per month.
    Detected by notes markers.
    """
    return (
        Invoice.objects.filter(
            property_profile=contract.property_profile,
            guest=contract.guest,
            booking__isnull=True,
        )
        .filter(Q(notes__icontains=f"Contract:{contract.id}") & Q(notes__icontains=f"Month:{ym}"))
        .order_by("-created_at")
        .first()
    )


def generate_monthly_invoice_for_contract(
    *,
    contract: Contract,
    year: int,
    month: int,
    issue: bool = True,
    tax_rate: Decimal = Decimal("0.000"),
) -> Invoice:
    """
    Generates ONE invoice per contract per month (idempotent).
    """
    if contract.status != ContractStatus.ACTIVE:
        raise ValueError("Contract must be ACTIVE to generate invoice")

    ym = f"{year:04d}-{month:02d}"

    existing = _find_existing_contract_month_invoice(contract, ym)
    if existing:
        return existing

    amount = compute_prorated_rent(contract, year, month)
    if amount <= Decimal("0.000"):
        raise ValueError("Calculated rent is zero for this month")

    inv = Invoice.objects.create(
        property_profile=contract.property_profile,
        booking=None,
        guest=contract.guest,
        status=InvoiceStatus.ISSUED if issue else InvoiceStatus.DRAFT,
        issue_date=timezone.localdate() if issue else None,
        currency=contract.currency or "OMR",
        notes=f"Monthly rent | Contract:{contract.id} | Unit:{contract.unit.code} | Month:{ym}",
    )
    inv.ensure_invoice_no()

    line = InvoiceLine.objects.create(
        invoice=inv,
        description=f"Monthly rent – {contract.unit.code} ({ym})",
        quantity=Decimal("1.000"),
        unit_price=amount,
        discount_amount=Decimal("0.000"),
        tax_rate=tax_rate,
    )
    line.recalc_tax()
    line.save(update_fields=["tax_amount"])

    inv.recalc_and_save()

    contract.last_invoiced_month = ym
    contract.save(update_fields=["last_invoiced_month", "updated_at"])

    return inv


def generate_monthly_invoices_for_property(
    *,
    property_profile_id: int,
    year: int,
    month: int,
    issue: bool = True,
    tax_rate: Decimal = Decimal("0.000"),
    dry_run: bool = False,
) -> dict:
    """
    Bulk generator for ALL active contracts in a property for a target month.
    Safe and idempotent.
    """
    ym = f"{year:04d}-{month:02d}"

    qs = (
        Contract.objects.select_related("property_profile", "unit", "guest")
        .filter(property_profile_id=property_profile_id, status=ContractStatus.ACTIVE)
        .order_by("id")
    )

    created = []
    existing = []
    failed = []

    for c in qs:
        try:
            ex = _find_existing_contract_month_invoice(c, ym)
            if ex:
                existing.append({"contract": c.id, "invoice": ex.id, "invoice_no": ex.invoice_no})
                continue

            if dry_run:
                created.append({"contract": c.id, "invoice": None, "invoice_no": None, "dry_run": True})
                continue

            inv = generate_monthly_invoice_for_contract(
                contract=c,
                year=year,
                month=month,
                issue=issue,
                tax_rate=tax_rate,
            )
            created.append({"contract": c.id, "invoice": inv.id, "invoice_no": inv.invoice_no})
        except Exception as e:
            failed.append({"contract": c.id, "error": str(e)})

    return {
        "property_profile": property_profile_id,
        "month": ym,
        "counts": {"created": len(created), "existing": len(existing), "failed": len(failed)},
        "created": created,
        "existing": existing,
        "failed": failed,
    }


# -----------------------
# Deposit invoice + payments (billing-recorded)
# -----------------------

def ensure_deposit_invoice(contract: Contract, *, issue: bool = True, tax_rate: Decimal = Decimal("0.000")) -> Invoice:
    """
    Creates (or returns) a deposit invoice linked to this contract.
    """
    if contract.deposit_invoice_id:
        inv = Invoice.objects.filter(id=contract.deposit_invoice_id).first()
        if inv:
            return inv

    if contract.security_deposit <= Decimal("0.000"):
        raise ValueError("security_deposit is 0, deposit invoice not required")

    inv = Invoice.objects.create(
        property_profile=contract.property_profile,
        booking=None,
        guest=contract.guest,
        status=InvoiceStatus.ISSUED if issue else InvoiceStatus.DRAFT,
        issue_date=timezone.localdate() if issue else None,
        currency=contract.currency or "OMR",
        notes=f"Security deposit | Contract:{contract.id} | Unit:{contract.unit.code}",
    )
    inv.ensure_invoice_no()

    line = InvoiceLine.objects.create(
        invoice=inv,
        description=f"Security deposit – {contract.unit.code}",
        quantity=Decimal("1.000"),
        unit_price=contract.security_deposit,
        discount_amount=Decimal("0.000"),
        tax_rate=tax_rate,
    )
    line.recalc_tax()
    line.save(update_fields=["tax_amount"])

    inv.recalc_and_save()

    contract.deposit_invoice = inv
    contract.save(update_fields=["deposit_invoice", "updated_at"])
    return inv


def record_deposit_payment_in(
    contract: Contract,
    *,
    amount: Decimal,
    method: str = PaymentMethod.CASH,
    reference: str = "",
    notes: str = "Deposit received",
) -> Payment:
    inv = ensure_deposit_invoice(contract, issue=True)
    p = Payment.objects.create(
        invoice=inv,
        property_profile=contract.property_profile,
        method=method,
        direction=PaymentDirection.IN,
        amount=amount,
        reference=reference,
        paid_at=timezone.now(),
        notes=notes,
    )
    inv.recalc_and_save()
    contract.mark_deposit_received(amount)
    return p


def record_deposit_refund_out(
    contract: Contract,
    *,
    amount: Decimal,
    method: str = PaymentMethod.CASH,
    reference: str = "",
    notes: str = "Deposit refund",
) -> Payment:
    inv = ensure_deposit_invoice(contract, issue=True)
    p = Payment.objects.create(
        invoice=inv,
        property_profile=contract.property_profile,
        method=method,
        direction=PaymentDirection.OUT,
        amount=amount,
        reference=reference,
        paid_at=timezone.now(),
        notes=notes,
    )
    inv.recalc_and_save()
    contract.mark_deposit_refunded(amount)
    return p