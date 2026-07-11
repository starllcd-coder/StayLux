from decimal import Decimal
from django.utils import timezone

from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status as drf_status
from rest_framework.parsers import MultiPartParser, FormParser

from core.viewsets import PropertyScopedModelViewSet
from core.permissions import IsReceptionOrHigher
from core.security import get_user_property_profile_id

from billing.serializers import InvoiceSerializer, PaymentSerializer
from billing.models import PaymentMethod

from notifications.services import queue_event_message
from audit.services import log_action
from audit.models import AuditAction
from settings_app.models import PropertyProfile

from inventory.models import UnitStatus
from housekeeping.models import HousekeepingTask, HousekeepingStatus

from .models import Contract, ContractDocument
from .serializers import ContractSerializer, ContractDocumentSerializer
from .services import (
    generate_monthly_invoice_for_contract,
    generate_monthly_invoices_for_property,
    ensure_deposit_invoice,
    record_deposit_payment_in,
    record_deposit_refund_out,
)


class ContractViewSet(PropertyScopedModelViewSet):
    queryset = Contract.objects.select_related("property_profile", "unit", "guest").all()
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticatedOrReadOnly & IsReceptionOrHigher]
    property_field_name = "property_profile"

    def get_queryset(self):
        qs = super().get_queryset()
        prop = self.get_property_profile()
        if prop:
            qs = qs.filter(unit__unit_type__business_type=prop.business_type)
        return qs

    def perform_create(self, serializer):
        contract: Contract = serializer.save()
        contract.update_deposit_status()
        contract.save(update_fields=["deposit_status", "updated_at"])

        log_action(
            property_profile=contract.property_profile,
            actor=self.request.user,
            object_type="contract",
            object_id=str(contract.id),
            action=AuditAction.CREATE,
            message="Contract created",
            metadata={"unit": contract.unit_id, "guest": contract.guest_id, "status": contract.status},
        )

    def perform_update(self, serializer):
        before = self.get_object()
        prev_status = before.status

        contract: Contract = serializer.save()
        contract.update_deposit_status()
        contract.save(update_fields=["deposit_status", "updated_at"])

        if prev_status != contract.status:
            log_action(
                property_profile=contract.property_profile,
                actor=self.request.user,
                object_type="contract",
                object_id=str(contract.id),
                action=AuditAction.STATUS_CHANGE,
                message=f"Contract status {prev_status} -> {contract.status}",
                metadata={"from": prev_status, "to": contract.status},
            )
        else:
            log_action(
                property_profile=contract.property_profile,
                actor=self.request.user,
                object_type="contract",
                object_id=str(contract.id),
                action=AuditAction.UPDATE,
                message="Contract updated",
                metadata={},
            )

    @action(detail=True, methods=["post"])
    def generate_invoice(self, request, pk=None):
        contract = self.get_object()

        year = request.data.get("year")
        month = request.data.get("month")
        if not year or not month:
            return Response({"detail": "year and month are required"}, status=drf_status.HTTP_400_BAD_REQUEST)

        issue = bool(request.data.get("issue", True))
        tax_rate = Decimal(str(request.data.get("tax_rate", "0.000")))

        try:
            inv = generate_monthly_invoice_for_contract(
                contract=contract,
                year=int(year),
                month=int(month),
                issue=issue,
                tax_rate=tax_rate,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=drf_status.HTTP_400_BAD_REQUEST)

        log_action(
            property_profile=contract.property_profile,
            actor=request.user,
            object_type="invoice",
            object_id=str(inv.id),
            action=AuditAction.CREATE,
            message="Monthly invoice generated from contract",
            metadata={"contract": contract.id, "invoice_no": inv.invoice_no},
        )

        if inv.status == "issued":
            queue_event_message(
                property_profile=inv.property_profile,
                event_key="invoice_issued",
                to_phone=(inv.guest.whatsapp or inv.guest.phone),
                context={
                    "guest_name": inv.guest.full_name,
                    "invoice_no": inv.invoice_no,
                    "total": str(inv.total),
                    "balance": str(inv.balance_due),
                },
            )

        return Response(InvoiceSerializer(inv).data, status=drf_status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def run_monthly_invoicing(self, request):
        if request.user.is_superuser and request.data.get("property_profile"):
            prop_id = int(request.data["property_profile"])
        else:
            prop_id = get_user_property_profile_id(request.user)

        if not prop_id:
            return Response({"detail": "property_profile could not be determined for this user."}, status=drf_status.HTTP_400_BAD_REQUEST)

        try:
            prop = PropertyProfile.objects.get(id=prop_id)
        except PropertyProfile.DoesNotExist:
            return Response({"detail": f"PropertyProfile {prop_id} not found"}, status=drf_status.HTTP_404_NOT_FOUND)

        today = timezone.localdate()
        year = int(request.data.get("year") or today.year)
        month = int(request.data.get("month") or today.month)

        issue = bool(request.data.get("issue", True))
        tax_rate = Decimal(str(request.data.get("tax_rate", "0.000")))
        dry_run = bool(request.data.get("dry_run", False))

        summary = generate_monthly_invoices_for_property(
            property_profile_id=prop_id,
            year=year,
            month=month,
            issue=issue,
            tax_rate=tax_rate,
            dry_run=dry_run,
        )

        log_action(
            property_profile=prop,
            actor=request.user,
            object_type="contracts",
            object_id=f"{prop_id}:{year:04d}-{month:02d}",
            action=AuditAction.CREATE,
            message="Run monthly invoicing (bulk)",
            metadata={"dry_run": dry_run, "counts": summary.get("counts", {})},
        )

        return Response(summary, status=drf_status.HTTP_200_OK)

    # Deposit invoice + payments
    @action(detail=True, methods=["post"])
    def create_deposit_invoice(self, request, pk=None):
        contract = self.get_object()
        tax_rate = Decimal(str(request.data.get("tax_rate", "0.000")))
        try:
            inv = ensure_deposit_invoice(contract, issue=True, tax_rate=tax_rate)
        except Exception as e:
            return Response({"detail": str(e)}, status=drf_status.HTTP_400_BAD_REQUEST)

        log_action(
            property_profile=contract.property_profile,
            actor=request.user,
            object_type="invoice",
            object_id=str(inv.id),
            action=AuditAction.CREATE,
            message="Deposit invoice created",
            metadata={"contract": contract.id, "invoice_no": inv.invoice_no},
        )

        return Response(InvoiceSerializer(inv).data, status=drf_status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def record_deposit_in(self, request, pk=None):
        contract = self.get_object()
        amount = request.data.get("amount")
        if not amount:
            return Response({"detail": "amount is required"}, status=drf_status.HTTP_400_BAD_REQUEST)

        method = request.data.get("method", PaymentMethod.CASH)
        reference = request.data.get("reference", "")
        notes = request.data.get("notes", "Deposit received")

        try:
            pay = record_deposit_payment_in(
                contract,
                amount=Decimal(str(amount)),
                method=method,
                reference=reference,
                notes=notes,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=drf_status.HTTP_400_BAD_REQUEST)

        log_action(
            property_profile=contract.property_profile,
            actor=request.user,
            object_type="payment",
            object_id=str(pay.id),
            action=AuditAction.CREATE,
            message="Deposit payment recorded (IN)",
            metadata={"contract": contract.id, "amount": str(amount), "method": method},
        )

        return Response(
            {"contract": ContractSerializer(contract).data, "payment": PaymentSerializer(pay).data},
            status=drf_status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def refund_deposit(self, request, pk=None):
        contract = self.get_object()
        amount = request.data.get("amount")
        if not amount:
            return Response({"detail": "amount is required"}, status=drf_status.HTTP_400_BAD_REQUEST)

        method = request.data.get("method", PaymentMethod.CASH)
        reference = request.data.get("reference", "")
        notes = request.data.get("notes", "Deposit refund")

        try:
            pay = record_deposit_refund_out(
                contract,
                amount=Decimal(str(amount)),
                method=method,
                reference=reference,
                notes=notes,
            )
        except Exception as e:
            return Response({"detail": str(e)}, status=drf_status.HTTP_400_BAD_REQUEST)

        log_action(
            property_profile=contract.property_profile,
            actor=request.user,
            object_type="payment",
            object_id=str(pay.id),
            action=AuditAction.CREATE,
            message="Deposit refund recorded (OUT)",
            metadata={"contract": contract.id, "amount": str(amount), "method": method},
        )

        return Response(
            {"contract": ContractSerializer(contract).data, "refund_payment": PaymentSerializer(pay).data},
            status=drf_status.HTTP_201_CREATED,
        )

    # Termination / Move-out
    @action(detail=True, methods=["post"])
    def terminate(self, request, pk=None):
        contract = self.get_object()

        end_date_str = request.data.get("end_date")
        if not end_date_str:
            return Response({"detail": "end_date is required (YYYY-MM-DD)"}, status=drf_status.HTTP_400_BAD_REQUEST)

        try:
            end_date = timezone.datetime.fromisoformat(end_date_str).date()
        except Exception:
            return Response({"detail": "end_date must be YYYY-MM-DD"}, status=drf_status.HTTP_400_BAD_REQUEST)

        terminated = bool(request.data.get("terminated", True))
        reason = str(request.data.get("reason", "")).strip()

        contract.mark_ended(end_date=end_date, move_out_date=end_date, reason=reason, terminated=terminated)

        unit = contract.unit
        unit.status = UnitStatus.HOUSEKEEPING
        unit.save(update_fields=["status", "updated_at"])

        hk_id = None
        if bool(request.data.get("create_housekeeping_task", True)):
            hk = HousekeepingTask.objects.create(
                property_profile=contract.property_profile,
                unit=unit,
                booking=None,
                status=HousekeepingStatus.PENDING,
                notes=f"Move-out cleaning for contract {contract.id}",
            )
            hk_id = hk.id

        log_action(
            property_profile=contract.property_profile,
            actor=request.user,
            object_type="contract",
            object_id=str(contract.id),
            action=AuditAction.STATUS_CHANGE,
            message="Contract terminated/ended",
            metadata={"status": contract.status, "end_date": str(contract.end_date), "reason": contract.termination_reason, "housekeeping_task": hk_id},
        )

        return Response({"contract": ContractSerializer(contract).data, "housekeeping_task_id": hk_id}, status=drf_status.HTTP_200_OK)


class ContractDocumentViewSet(PropertyScopedModelViewSet):
    """
    Upload & manage contract documents.

    POST expects multipart/form-data:
      property_profile: 1
      contract: 1
      doc_type: signed_agreement
      title: "Signed agreement Feb 2026"
      file: <upload>
      notes: ...
    """
    queryset = ContractDocument.objects.select_related("property_profile", "contract").all()
    serializer_class = ContractDocumentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly & IsReceptionOrHigher]
    property_field_name = "property_profile"
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        qs = super().get_queryset()
        prop = self.get_property_profile()
        if prop:
            qs = qs.filter(contract__unit__unit_type__business_type=prop.business_type)
        return qs

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def perform_create(self, serializer):
        doc: ContractDocument = serializer.save()
        log_action(
            property_profile=doc.property_profile,
            actor=self.request.user,
            object_type="contract_document",
            object_id=str(doc.id),
            action=AuditAction.CREATE,
            message="Contract document uploaded",
            metadata={"contract": doc.contract_id, "doc_type": doc.doc_type, "title": doc.title},
        )