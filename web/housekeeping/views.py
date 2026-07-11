from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status as drf_status

from core.viewsets import PropertyScopedModelViewSet
from core.permissions import IsHousekeepingOrHigher
from .models import HousekeepingTask
from .serializers import HousekeepingTaskSerializer

from accounts.models import StaffProfile
from audit.services import log_action
from audit.models import AuditAction


class HousekeepingTaskViewSet(PropertyScopedModelViewSet):
    queryset = HousekeepingTask.objects.select_related("property_profile", "unit", "booking", "assigned_to").all()
    serializer_class = HousekeepingTaskSerializer
    permission_classes = [IsAuthenticatedOrReadOnly & IsHousekeepingOrHigher]
    property_field_name = "property_profile"

    def get_queryset(self):
        qs = super().get_queryset()

        prop = self.get_property_profile()
        if prop:
            qs = qs.filter(unit__unit_type__business_type=prop.business_type)

        unit = self.request.query_params.get("unit")
        if unit:
            qs = qs.filter(unit_id=unit)

        status_q = self.request.query_params.get("status")
        if status_q:
            qs = qs.filter(status=status_q)

        assigned_to = self.request.query_params.get("assigned_to")
        if assigned_to:
            qs = qs.filter(assigned_to_id=assigned_to)

        return qs

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        task = self.get_object()
        staff_id = request.data.get("assigned_to")
        if not staff_id:
            return Response({"detail": "assigned_to is required"}, status=drf_status.HTTP_400_BAD_REQUEST)

        staff = StaffProfile.objects.filter(id=staff_id).first()
        if not staff:
            return Response({"detail": "StaffProfile not found"}, status=drf_status.HTTP_404_NOT_FOUND)

        task.assigned_to = staff
        task.save(update_fields=["assigned_to", "updated_at"])

        log_action(
            property_profile=task.property_profile,
            actor=request.user,
            object_type="housekeeping_task",
            object_id=str(task.id),
            action=AuditAction.ASSIGN,
            message="Housekeeping task assigned",
            metadata={"assigned_to": staff.id},
        )

        return Response(HousekeepingTaskSerializer(task).data, status=drf_status.HTTP_200_OK)