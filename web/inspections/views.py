from decimal import Decimal
from django.utils import timezone

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status as drf_status

from core.viewsets import PropertyScopedModelViewSet
from core.permissions import IsReceptionOrHigher

from audit.services import log_action
from audit.models import AuditAction

from billing.serializers import PaymentSerializer
from billing.models import PaymentMethod

from .models import MoveOutInspection
from .serializers import MoveOutInspectionSerializer
from .services import complete_moveout_inspection


class MoveOutInspectionViewSet(PropertyScopedModelViewSet):
    queryset = MoveOutInspection.objects.select_related("property_profile", "contract", "contract__unit", "contract__guest").all()
    serializer_class = MoveOutInspectionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly & IsReceptionOrHigher]
    property_field_name = "property_profile"

    def get_queryset(self):
        qs = super().get_queryset()
        prop = self.get_property_profile()
        if prop:
            qs = qs.filter(contract__unit__unit_type__business_type=prop.business_type)
        return qs

    def perform_create(self, serializer):
        obj: MoveOutInspection = serializer.save()
        log_action(
            property_profile=obj.property_profile,
            actor=self.request.user,
            object_type="moveout_inspection",
            object_id=str(obj.id),
            action=AuditAction.CREATE,
            message="Move-out inspection created",
            metadata={"contract": obj.contract_id},
        )

    def perform_update(self, serializer):
        obj: MoveOutInspection = serializer.save()
        log_action(
            property_profile=obj.property_profile,
            actor=self.request.user,
            object_type="moveout_inspection",
            object_id=str(obj.id),
            action=AuditAction.UPDATE,
            message="Move-out inspection updated",
            metadata={},
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """
        POST /api/moveout-inspections/{id}/complete/
        Body:
          {
            "deductions": "10.000",
            "auto_refund": true,
            "refund_method": "cash",
            "refund_reference": "",
            "refund_notes": "",
            "end_contract": true,
            "terminated": false,
            "end_date": "2026-02-22",
            "reason": "Move-out",
            "create_housekeeping_task": true
          }
        """
        inspection = self.get_object()

        deductions = Decimal(str(request.data.get("deductions", "0.000")))
        auto_refund = bool(request.data.get("auto_refund", True))
        refund_method = request.data.get("refund_method", PaymentMethod.CASH)
        refund_reference = request.data.get("refund_reference", "")
        refund_notes = request.data.get("refund_notes", "")

        end_contract = bool(request.data.get("end_contract", True))
        terminated = bool(request.data.get("terminated", False))
        end_date_str = request.data.get("end_date")
        if end_contract and not end_date_str:
            return Response({"detail": "end_date is required when end_contract=true"}, status=drf_status.HTTP_400_BAD_REQUEST)

        if end_contract:
            try:
                end_date = timezone.datetime.fromisoformat(end_date_str).date()
            except Exception:
                return Response({"detail": "end_date must be YYYY-MM-DD"}, status=drf_status.HTTP_400_BAD_REQUEST)
        else:
            end_date = timezone.localdate()

        reason = str(request.data.get("reason", "")).strip()
        create_housekeeping_task = bool(request.data.get("create_housekeeping_task", True))

        result = complete_moveout_inspection(
            inspection=inspection,
            deductions=deductions,
            auto_refund=auto_refund,
            refund_method=refund_method,
            refund_reference=refund_reference,
            refund_notes=refund_notes,
            end_contract=end_contract,
            terminated=terminated,
            end_date=end_date,
            reason=reason,
            create_housekeeping_task=create_housekeeping_task,
        )

        refund_payment = result["refund_payment"]

        log_action(
            property_profile=inspection.property_profile,
            actor=request.user,
            object_type="moveout_inspection",
            object_id=str(inspection.id),
            action=AuditAction.STATUS_CHANGE,
            message="Move-out inspection completed",
            metadata={
                "contract": inspection.contract_id,
                "deductions": str(deductions),
                "refundable_amount": str(result["refundable_amount"]),
                "auto_refund": auto_refund,
                "housekeeping_task_id": result["housekeeping_task_id"],
            },
        )

        return Response(
            {
                "inspection": MoveOutInspectionSerializer(result["inspection"]).data,
                "housekeeping_task_id": result["housekeeping_task_id"],
                "refundable_amount": str(result["refundable_amount"]),
                "refund_payment": PaymentSerializer(refund_payment).data if refund_payment else None,
            },
            status=drf_status.HTTP_200_OK,
        )