from __future__ import annotations

from decimal import Decimal
from django.utils import timezone

from contracts.models import Contract, ContractStatus
from contracts.services import record_deposit_refund_out
from inventory.models import UnitStatus
from housekeeping.models import HousekeepingTask, HousekeepingStatus
from .models import MoveOutInspection, InspectionStatus


def compute_refundable(contract: Contract, deductions: Decimal) -> Decimal:
    """
    refundable = min(deposit_received, security_deposit) - deposit_refunded - deductions
    never below 0
    """
    received_cap = min(contract.deposit_received, contract.security_deposit)
    refundable = received_cap - contract.deposit_refunded - deductions
    if refundable < Decimal("0.000"):
        refundable = Decimal("0.000")
    return refundable


def complete_moveout_inspection(
    *,
    inspection: MoveOutInspection,
    deductions: Decimal,
    auto_refund: bool,
    refund_method: str,
    refund_reference: str,
    refund_notes: str,
    end_contract: bool,
    terminated: bool,
    end_date,
    reason: str,
    create_housekeeping_task: bool,
) -> dict:
    contract = inspection.contract

    inspection.deductions = deductions
    inspection.refundable_amount = compute_refundable(contract, deductions)
    inspection.status = InspectionStatus.COMPLETED
    if not inspection.inspection_date:
        inspection.inspection_date = timezone.localdate()
    inspection.save(update_fields=["deductions", "refundable_amount", "status", "inspection_date", "updated_at"])

    hk_id = None
    refund_payment = None

    # Update unit to housekeeping (typical move-out flow)
    unit = contract.unit
    unit.status = UnitStatus.HOUSEKEEPING
    unit.save(update_fields=["status", "updated_at"])

    if create_housekeeping_task:
        hk = HousekeepingTask.objects.create(
            property_profile=contract.property_profile,
            unit=unit,
            booking=None,
            status=HousekeepingStatus.PENDING,
            notes=f"Move-out cleaning (contract {contract.id})",
        )
        hk_id = hk.id

    # Optionally end/terminate contract
    if end_contract:
        contract.mark_ended(end_date=end_date, move_out_date=end_date, reason=reason or "", terminated=terminated)

    # Optionally auto-refund (billing Payment OUT)
    if auto_refund and inspection.refundable_amount > Decimal("0.000"):
        refund_payment = record_deposit_refund_out(
            contract,
            amount=inspection.refundable_amount,
            method=refund_method,
            reference=refund_reference,
            notes=refund_notes or "Deposit refund after move-out inspection",
        )

    return {
        "inspection": inspection,
        "housekeeping_task_id": hk_id,
        "refund_payment": refund_payment,
        "refundable_amount": inspection.refundable_amount,
    }