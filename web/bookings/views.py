from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status as drf_status
from django.utils import timezone

from core.viewsets import PropertyScopedModelViewSet
from core.permissions import IsReceptionOrHigher
from audit.services import log_action
from audit.models import AuditAction

from inventory.models import UnitStatus

from .models import Booking, BookingStatus, BookingType, is_unit_available
from .serializers import BookingSerializer
from .services import auto_fill_rate_if_missing


class BookingViewSet(PropertyScopedModelViewSet):
    queryset = Booking.objects.select_related("property_profile", "unit", "guest").all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticatedOrReadOnly & IsReceptionOrHigher]
    property_field_name = "property_profile"

    def get_queryset(self):
        qs = super().get_queryset()
        include_archived = self.request.query_params.get("include_archived") == "1"
        if not include_archived:
            qs = qs.filter(is_archived=False)
        prop = self.get_property_profile()
        if prop:
            booking_type = BookingType.HOTEL if prop.business_type == "hotel" else BookingType.APARTMENT
            qs = qs.filter(booking_type=booking_type)
        return qs

    def perform_create(self, serializer):
        booking: Booking = serializer.save()

        if not is_unit_available(
            booking.unit_id,
            booking.start_date,
            booking.end_date,
            exclude_booking_id=booking.id,
        ):
            booking.delete()
            raise ValueError("Unit is not available for the selected dates.")

        updated_fields = auto_fill_rate_if_missing(booking)
        if updated_fields:
            booking.save(update_fields=updated_fields + ["updated_at"])

        log_action(
            property_profile=booking.property_profile,
            actor=self.request.user,
            object_type="booking",
            object_id=str(booking.id),
            action=AuditAction.CREATE,
            message="Booking created",
            metadata={
                "unit": booking.unit_id,
                "guest": booking.guest_id,
                "status": booking.status,
                "booking_type": booking.booking_type,
                "rent_cycle": booking.rent_cycle,
                "start_date": str(booking.start_date),
                "end_date": str(booking.end_date),
                "rate": str(booking.rate),
                "discount": str(booking.discount),
                "deposit": str(booking.deposit),
                "total_estimated": str(booking.estimate_total()),
            },
        )

    def perform_update(self, serializer):
        booking: Booking = serializer.save()

        if not is_unit_available(
            booking.unit_id,
            booking.start_date,
            booking.end_date,
            exclude_booking_id=booking.id,
        ):
            raise ValueError("Unit is not available for the selected dates.")

        # If locked, prevent price edits silently (or you can raise error)
        if booking.price_locked:
            # Do nothing extra; estimate_total will use locked_total
            pass

        log_action(
            property_profile=booking.property_profile,
            actor=self.request.user,
            object_type="booking",
            object_id=str(booking.id),
            action=AuditAction.UPDATE,
            message="Booking updated",
            metadata={"total_estimated": str(booking.estimate_total())},
        )

    @action(detail=True, methods=["post"])
    def reprice(self, request, pk=None):
        booking = self.get_object()

        if booking.price_locked:
            return Response({"detail": "Pricing is locked for this booking."}, status=drf_status.HTTP_400_BAD_REQUEST)

        updated_fields = auto_fill_rate_if_missing(booking)
        if updated_fields:
            booking.save(update_fields=updated_fields + ["updated_at"])

        log_action(
            property_profile=booking.property_profile,
            actor=request.user,
            object_type="booking",
            object_id=str(booking.id),
            action=AuditAction.UPDATE,
            message="Booking repriced",
            metadata={"rate": str(booking.rate), "discount": str(booking.discount), "total_estimated": str(booking.estimate_total())},
        )
        return Response(BookingSerializer(booking).data, status=drf_status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def check_in(self, request, pk=None):
        booking = self.get_object()

        if booking.status in [BookingStatus.CANCELLED, BookingStatus.NO_SHOW]:
            return Response({"detail": f"Cannot check-in a {booking.status} booking."}, status=drf_status.HTTP_400_BAD_REQUEST)

        booking.status = BookingStatus.CHECKED_IN

        # ✅ lock pricing at check-in
        if not booking.price_locked:
            booking.lock_pricing()

        booking.save(update_fields=[
            "status",
            "price_locked", "locked_at", "locked_rate", "locked_discount", "locked_deposit", "locked_total",
            "updated_at",
        ])

        booking.unit.status = UnitStatus.OCCUPIED
        booking.unit.save(update_fields=["status", "updated_at"])

        log_action(
            property_profile=booking.property_profile,
            actor=request.user,
            object_type="booking",
            object_id=str(booking.id),
            action=AuditAction.STATUS_CHANGE,
            message="Booking checked in",
            metadata={"status": booking.status, "locked_total": str(booking.locked_total)},
        )

        return Response(BookingSerializer(booking).data, status=drf_status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def check_out(self, request, pk=None):
        booking = self.get_object()

        if booking.status not in [BookingStatus.CHECKED_IN, BookingStatus.RESERVED]:
            return Response({"detail": f"Cannot check-out booking in status {booking.status}."}, status=drf_status.HTTP_400_BAD_REQUEST)

        checkout_date = timezone.localdate()
        if booking.end_date and booking.end_date > checkout_date:
            booking.end_date = checkout_date
        booking.status = BookingStatus.CHECKED_OUT
        booking.save(update_fields=["status", "end_date", "updated_at"])

        booking.unit.status = UnitStatus.HOUSEKEEPING
        booking.unit.save(update_fields=["status", "updated_at"])

        log_action(
            property_profile=booking.property_profile,
            actor=request.user,
            object_type="booking",
            object_id=str(booking.id),
            action=AuditAction.STATUS_CHANGE,
            message="Booking checked out",
            metadata={"status": booking.status},
        )

        return Response(BookingSerializer(booking).data, status=drf_status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = self.get_object()

        if booking.status == BookingStatus.CHECKED_OUT:
            return Response({"detail": "Cannot cancel a checked-out booking."}, status=drf_status.HTTP_400_BAD_REQUEST)

        booking.status = BookingStatus.CANCELLED
        booking.save(update_fields=["status", "updated_at"])

        log_action(
            property_profile=booking.property_profile,
            actor=request.user,
            object_type="booking",
            object_id=str(booking.id),
            action=AuditAction.STATUS_CHANGE,
            message="Booking cancelled",
            metadata={"status": booking.status},
        )
        return Response(BookingSerializer(booking).data, status=drf_status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def no_show(self, request, pk=None):
        booking = self.get_object()

        if booking.status in [BookingStatus.CHECKED_IN, BookingStatus.CHECKED_OUT]:
            return Response({"detail": "Cannot mark no-show after check-in/out."}, status=drf_status.HTTP_400_BAD_REQUEST)

        booking.status = BookingStatus.NO_SHOW
        booking.save(update_fields=["status", "updated_at"])

        log_action(
            property_profile=booking.property_profile,
            actor=request.user,
            object_type="booking",
            object_id=str(booking.id),
            action=AuditAction.STATUS_CHANGE,
            message="Booking marked as no-show",
            metadata={"status": booking.status},
        )
        return Response(BookingSerializer(booking).data, status=drf_status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        booking = self.get_object()
        booking.archive()
        booking.save(update_fields=["is_archived", "archived_at", "updated_at"])

        log_action(
            property_profile=booking.property_profile,
            actor=request.user,
            object_type="booking",
            object_id=str(booking.id),
            action=AuditAction.UPDATE,
            message="Booking archived",
            metadata={},
        )
        return Response({"detail": "Archived"}, status=drf_status.HTTP_200_OK)

    # ⚠️ Booking → Invoice hook (stub)
    # Once you share billing models, I will wire this fully.
    @action(detail=True, methods=["post"])
    def create_invoice(self, request, pk=None):
        booking = self.get_object()
        return Response(
            {
                "detail": "Invoice integration is not wired yet. Upload billing/models.py (Invoice + lines) and I will connect this endpoint fully."
            },
            status=drf_status.HTTP_501_NOT_IMPLEMENTED,
        )