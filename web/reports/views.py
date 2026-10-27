from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as drf_status
from rest_framework.permissions import IsAuthenticated

from inventory.models import Unit, UnitStatus
from bookings.models import Booking, BookingStatus, BookingType
from billing.models import Invoice, Payment
from housekeeping.models import HousekeepingTask, HousekeepingStatus
from maintenance.models import MaintenanceRequest, MaintenanceStatus
from accounts.models import OwnerProfile
from settings_app.models import PropertyProfile


def _get_date_range(request, default_days: int = 30):
    return _date_range_from_params(request.query_params, default_days)


def _date_range_from_params(params, default_days: int = 30):
    today = timezone.localdate()
    period = (params.get("period") or "").strip().lower()

    if period == "daily":
        return today, today
    if period == "weekly":
        return today - timedelta(days=6), today
    if period == "monthly":
        return today - timedelta(days=29), today

    sd = parse_date(params.get("start_date") or "")
    ed = parse_date(params.get("end_date") or "")

    if not ed:
        ed = today
    if not sd:
        sd = ed - timedelta(days=default_days)

    if sd > ed:
        sd, ed = ed, sd

    return sd, ed


def _require_property_profile(request):
    prop = request.query_params.get("property_profile")
    if not prop:
        return None, Response({"detail": "property_profile is required"}, status=drf_status.HTTP_400_BAD_REQUEST)
    try:
        prop_id = int(prop)
    except ValueError:
        return None, Response({"detail": "property_profile must be an integer"}, status=drf_status.HTTP_400_BAD_REQUEST)
    return prop_id, None


def _get_property_profile(request):
    prop_id, err = _require_property_profile(request)
    if err:
        return None, err
    prop = PropertyProfile.objects.filter(id=prop_id).first()
    if not prop:
        return None, Response({"detail": f"PropertyProfile {prop_id} not found"}, status=drf_status.HTTP_404_NOT_FOUND)
    return prop, None


def _authorize_property_access(request, prop: PropertyProfile):
    if request.user.is_superuser:
        return None

    owner_profile = getattr(request.user, "owner_profile", None)
    if owner_profile:
        return Response(
            {"detail": "Owners can only access owner-dashboard endpoint"},
            status=drf_status.HTTP_403_FORBIDDEN,
        )

    staff_profile = getattr(request.user, "staff_profile", None)
    if staff_profile and staff_profile.property_id == prop.id:
        return None

    return Response({"detail": "You do not have access to this property"}, status=drf_status.HTTP_403_FORBIDDEN)


def _current_booking_type(prop):
    return BookingType.HOTEL if getattr(prop, "business_type", "hotel") == "hotel" else BookingType.APARTMENT


def _filter_invoices_for_mode(qs, prop):
    booking_type = _current_booking_type(prop)
    return qs.filter(
        Q(booking__booking_type=booking_type)
        | Q(booking__isnull=True, guest__business_type=prop.business_type)
    )


def _filter_payments_for_mode(qs, prop):
    booking_type = _current_booking_type(prop)
    return qs.filter(
        Q(invoice__booking__booking_type=booking_type)
        | Q(invoice__booking__isnull=True, invoice__guest__business_type=prop.business_type)
    )


class OwnerDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prop, err = _get_property_profile(request)
        if err:
            return err
        auth_err = _authorize_property_access(request, prop)
        if auth_err:
            return auth_err

        sd, ed = _get_date_range(request)
        ed_excl = ed + timedelta(days=1)

        total_units = Unit.objects.filter(
            property_profile_id=prop.id,
            is_active=True,
            unit_type__business_type=prop.business_type,
        ).count()
        units_by_status = (
            Unit.objects.filter(property_profile_id=prop.id, is_active=True, unit_type__business_type=prop.business_type)
            .values("status")
            .annotate(count=Count("id"))
        )
        units_by_status_map = {row["status"]: row["count"] for row in units_by_status}

        total_unit_nights = total_units * max((ed - sd).days, 1)
        booked_nights = 0

        booking_type = _current_booking_type(prop)
        bookings = Booking.objects.filter(
            property_profile_id=prop.id,
            booking_type=booking_type,
            unit__unit_type__business_type=prop.business_type,
        ).exclude(
            status__in=[BookingStatus.CANCELLED, BookingStatus.NO_SHOW]
        ).filter(start_date__lt=ed_excl, end_date__gt=sd)

        for b in bookings.only("start_date", "end_date"):
            overlap_start = max(b.start_date, sd)
            overlap_end = min(b.end_date, ed_excl)
            nights = max((overlap_end - overlap_start).days, 0)
            booked_nights += nights

        occupancy_pct = 0.0
        if total_unit_nights > 0:
            occupancy_pct = round((booked_nights / total_unit_nights) * 100.0, 2)

        inv_qs = Invoice.objects.filter(property_profile_id=prop.id, created_at__date__gte=sd, created_at__date__lte=ed)
        inv_qs = _filter_invoices_for_mode(inv_qs, prop)
        revenue_total = inv_qs.aggregate(s=Sum("total"))["s"] or Decimal("0.000")
        outstanding_total = inv_qs.aggregate(s=Sum("balance_due"))["s"] or Decimal("0.000")

        pay_qs = Payment.objects.filter(
            property_profile_id=prop.id,
            is_void=False,
            created_at__date__gte=sd,
            created_at__date__lte=ed,
        )
        pay_qs = _filter_payments_for_mode(pay_qs, prop)
        collections_total = pay_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0.000")

        hk_qs = HousekeepingTask.objects.filter(
            property_profile_id=prop.id,
            created_at__date__gte=sd,
            created_at__date__lte=ed,
            unit__unit_type__business_type=prop.business_type,
        )
        hk_by_status = hk_qs.values("status").annotate(count=Count("id"))
        hk_by_status_map = {row["status"]: row["count"] for row in hk_by_status}

        m_qs = MaintenanceRequest.objects.filter(
            property_profile_id=prop.id,
            created_at__date__gte=sd,
            created_at__date__lte=ed,
            unit__unit_type__business_type=prop.business_type,
        )
        m_by_status = m_qs.values("status").annotate(count=Count("id"))
        m_by_status_map = {row["status"]: row["count"] for row in m_by_status}

        return Response(
            {
                "property_profile": prop.id,
                "range": {"start_date": str(sd), "end_date": str(ed)},
                "units": {
                    "total_units": total_units,
                    "by_status": units_by_status_map,
                    "available": units_by_status_map.get(UnitStatus.AVAILABLE, 0),
                    "occupied": units_by_status_map.get(UnitStatus.OCCUPIED, 0),
                    "housekeeping": units_by_status_map.get(UnitStatus.HOUSEKEEPING, 0),
                    "maintenance": units_by_status_map.get(UnitStatus.MAINTENANCE, 0),
                },
                "occupancy": {
                    "total_unit_nights": total_unit_nights,
                    "booked_nights": booked_nights,
                    "occupancy_percent": occupancy_pct,
                },
                "billing": {
                    "revenue_total": str(revenue_total),
                    "collections_total": str(collections_total),
                    "outstanding_total": str(outstanding_total),
                },
                "housekeeping": {
                    "total_tasks": hk_qs.count(),
                    "by_status": hk_by_status_map,
                    "pending": hk_by_status_map.get(HousekeepingStatus.PENDING, 0),
                    "in_progress": hk_by_status_map.get(HousekeepingStatus.IN_PROGRESS, 0),
                    "done": hk_by_status_map.get(HousekeepingStatus.DONE, 0),
                },
                "maintenance": {
                    "total_requests": m_qs.count(),
                    "by_status": m_by_status_map,
                    "open": m_by_status_map.get(MaintenanceStatus.OPEN, 0),
                    "in_progress": m_by_status_map.get(MaintenanceStatus.IN_PROGRESS, 0),
                    "resolved": m_by_status_map.get(MaintenanceStatus.RESOLVED, 0),
                },
            },
            status=drf_status.HTTP_200_OK,
        )


class OccupancyReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prop, err = _get_property_profile(request)
        if err:
            return err
        auth_err = _authorize_property_access(request, prop)
        if auth_err:
            return auth_err

        sd, ed = _get_date_range(request)
        ed_excl = ed + timedelta(days=1)

        total_units = Unit.objects.filter(
            property_profile_id=prop.id,
            is_active=True,
            unit_type__business_type=prop.business_type,
        ).count()
        total_unit_nights = total_units * max((ed - sd).days, 1)

        booking_type = _current_booking_type(prop)
        bookings = Booking.objects.filter(
            property_profile_id=prop.id,
            booking_type=booking_type,
            unit__unit_type__business_type=prop.business_type,
        ).exclude(
            status__in=[BookingStatus.CANCELLED, BookingStatus.NO_SHOW]
        ).filter(start_date__lt=ed_excl, end_date__gt=sd)

        booked_nights = 0
        for b in bookings.only("start_date", "end_date"):
            overlap_start = max(b.start_date, sd)
            overlap_end = min(b.end_date, ed_excl)
            booked_nights += max((overlap_end - overlap_start).days, 0)

        occupancy_pct = 0.0
        if total_unit_nights > 0:
            occupancy_pct = round((booked_nights / total_unit_nights) * 100.0, 2)

        return Response(
            {
                "property_profile": prop.id,
                "range": {"start_date": str(sd), "end_date": str(ed)},
                "total_units": total_units,
                "total_unit_nights": total_unit_nights,
                "booked_nights": booked_nights,
                "occupancy_percent": occupancy_pct,
                "active_bookings_count": bookings.count(),
            },
            status=drf_status.HTTP_200_OK,
        )


class RevenueReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prop, err = _get_property_profile(request)
        if err:
            return err
        auth_err = _authorize_property_access(request, prop)
        if auth_err:
            return auth_err

        sd, ed = _get_date_range(request)

        inv_qs = Invoice.objects.filter(property_profile_id=prop.id, created_at__date__gte=sd, created_at__date__lte=ed)
        inv_qs = _filter_invoices_for_mode(inv_qs, prop)
        pay_qs = Payment.objects.filter(property_profile_id=prop.id, is_void=False, created_at__date__gte=sd, created_at__date__lte=ed)
        pay_qs = _filter_payments_for_mode(pay_qs, prop)

        revenue_total = inv_qs.aggregate(s=Sum("total"))["s"] or Decimal("0.000")
        tax_total = inv_qs.aggregate(s=Sum("tax_total"))["s"] or Decimal("0.000")
        outstanding_total = inv_qs.aggregate(s=Sum("balance_due"))["s"] or Decimal("0.000")
        collections_total = pay_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0.000")

        collections_by_method = pay_qs.values("method").annotate(total=Sum("amount")).order_by("method")
        collections_by_method_map = {row["method"]: str(row["total"] or Decimal("0.000")) for row in collections_by_method}

        return Response(
            {
                "property_profile": prop.id,
                "range": {"start_date": str(sd), "end_date": str(ed)},
                "invoices": {
                    "count": inv_qs.count(),
                    "revenue_total": str(revenue_total),
                    "tax_total": str(tax_total),
                    "outstanding_total": str(outstanding_total),
                },
                "payments": {
                    "count": pay_qs.count(),
                    "collections_total": str(collections_total),
                    "by_method": collections_by_method_map,
                },
            },
            status=drf_status.HTTP_200_OK,
        )


class AgingReportView(APIView):
    """
    GET /api/reports/aging/?property_profile=1
    Buckets: 0-30, 31-60, 61-90, 90+
    Uses invoice.created_at date as age baseline.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        prop, err = _get_property_profile(request)
        if err:
            return err
        auth_err = _authorize_property_access(request, prop)
        if auth_err:
            return auth_err

        today = timezone.localdate()

        # only invoices with outstanding balance
        qs = Invoice.objects.filter(property_profile_id=prop.id).exclude(status="void").filter(balance_due__gt=Decimal("0.000"))
        qs = _filter_invoices_for_mode(qs, prop)

        b0_30 = Decimal("0.000")
        b31_60 = Decimal("0.000")
        b61_90 = Decimal("0.000")
        b90p = Decimal("0.000")

        count0_30 = count31_60 = count61_90 = count90p = 0

        for inv in qs.only("id", "invoice_no", "created_at", "balance_due"):
            age_days = (today - inv.created_at.date()).days
            bal = inv.balance_due

            if age_days <= 30:
                b0_30 += bal
                count0_30 += 1
            elif age_days <= 60:
                b31_60 += bal
                count31_60 += 1
            elif age_days <= 90:
                b61_90 += bal
                count61_90 += 1
            else:
                b90p += bal
                count90p += 1

        total_outstanding = (b0_30 + b31_60 + b61_90 + b90p)

        return Response(
            {
                "property_profile": prop.id,
                "as_of": str(today),
                "total_outstanding": str(total_outstanding),
                "buckets": [
                    {"label": "0-30", "count": count0_30, "amount": str(b0_30)},
                    {"label": "31-60", "count": count31_60, "amount": str(b31_60)},
                    {"label": "61-90", "count": count61_90, "amount": str(b61_90)},
                    {"label": "90+", "count": count90p, "amount": str(b90p)},
                ],
            },
            status=drf_status.HTTP_200_OK,
        )


class OwnerUnitsDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        owner_profile = getattr(request.user, "owner_profile", None)
        if not owner_profile or not owner_profile.is_active:
            return Response({"detail": "Active owner profile is required"}, status=drf_status.HTTP_403_FORBIDDEN)

        owner = OwnerProfile.objects.select_related("property", "user").filter(id=owner_profile.id, is_active=True).first()
        if not owner:
            return Response({"detail": "owner_profile not found"}, status=drf_status.HTTP_404_NOT_FOUND)

        return Response(build_owner_units_dashboard(owner, request.query_params))


def build_owner_units_dashboard(owner, params):
    """Build metrics for this owner's assigned units for both HTML and API views."""
    sd, ed = _date_range_from_params(params, default_days=30)
    ed_excl = ed + timedelta(days=1)
    selected_period = (params.get("period") or "").strip().lower() or "custom"

    unit_ids = list(
        owner.units.filter(
            is_active=True,
            property_profile_id=owner.property_id,
            unit_type__business_type=owner.property.business_type,
        ).values_list("id", flat=True)
    )
    total_units = len(unit_ids)
    units_by_status = (
        Unit.objects.filter(id__in=unit_ids, is_active=True)
        .values("status")
        .annotate(count=Count("id"))
    )
    units_by_status_map = {row["status"]: row["count"] for row in units_by_status}

    total_unit_nights = total_units * max((ed_excl - sd).days, 1)
    booked_nights = 0

    booking_type = _current_booking_type(owner.property)
    bookings = Booking.objects.filter(unit_id__in=unit_ids, booking_type=booking_type).exclude(
        status__in=[BookingStatus.CANCELLED, BookingStatus.NO_SHOW]
    ).filter(start_date__lt=ed_excl, end_date__gt=sd)

    for b in bookings.only("start_date", "end_date"):
        overlap_start = max(b.start_date, sd)
        overlap_end = min(b.end_date, ed_excl)
        nights = max((overlap_end - overlap_start).days, 0)
        booked_nights += nights

    occupancy_pct = 0.0
    if total_unit_nights > 0:
        occupancy_pct = round((booked_nights / total_unit_nights) * 100.0, 2)

    inv_qs = Invoice.objects.filter(
        property_profile_id=owner.property_id,
        booking__unit_id__in=unit_ids,
        created_at__date__gte=sd,
        created_at__date__lte=ed,
    )
    inv_qs = _filter_invoices_for_mode(inv_qs, owner.property)
    revenue_total = inv_qs.aggregate(s=Sum("total"))["s"] or Decimal("0.000")
    outstanding_total = inv_qs.aggregate(s=Sum("balance_due"))["s"] or Decimal("0.000")

    pay_qs = Payment.objects.filter(
        property_profile_id=owner.property_id,
        invoice__booking__unit_id__in=unit_ids,
        is_void=False,
        created_at__date__gte=sd,
        created_at__date__lte=ed,
    )
    pay_qs = _filter_payments_for_mode(pay_qs, owner.property)
    collections_total = pay_qs.aggregate(s=Sum("amount"))["s"] or Decimal("0.000")

    hk_qs = HousekeepingTask.objects.filter(
        property_profile_id=owner.property_id,
        unit_id__in=unit_ids,
        created_at__date__gte=sd,
        created_at__date__lte=ed,
    )
    hk_by_status = hk_qs.values("status").annotate(count=Count("id"))
    hk_by_status_map = {row["status"]: row["count"] for row in hk_by_status}

    m_qs = MaintenanceRequest.objects.filter(
        property_profile_id=owner.property_id,
        unit_id__in=unit_ids,
        created_at__date__gte=sd,
        created_at__date__lte=ed,
    )
    m_by_status = m_qs.values("status").annotate(count=Count("id"))
    m_by_status_map = {row["status"]: row["count"] for row in m_by_status}
    maintenance_total_cost = m_qs.aggregate(s=Sum("total_cost"))["s"] or Decimal("0.000")
    net_income_total = revenue_total - maintenance_total_cost

    return {
        "owner_profile": owner.id,
        "property_profile": owner.property_id,
        "range": {"start_date": str(sd), "end_date": str(ed)},
        "period": selected_period,
        "units": {
            "total_units": total_units,
            "by_status": units_by_status_map,
            "available": units_by_status_map.get(UnitStatus.AVAILABLE, 0),
            "occupied": units_by_status_map.get(UnitStatus.OCCUPIED, 0),
            "housekeeping": units_by_status_map.get(UnitStatus.HOUSEKEEPING, 0),
            "maintenance": units_by_status_map.get(UnitStatus.MAINTENANCE, 0),
        },
        "occupancy": {
            "total_unit_nights": total_unit_nights,
            "booked_nights": booked_nights,
            "occupancy_percent": occupancy_pct,
        },
        "billing": {
            "revenue_total": format(revenue_total, ".3f"),
            "collections_total": format(collections_total, ".3f"),
            "outstanding_total": format(outstanding_total, ".3f"),
            "total_income": format(net_income_total, ".3f"),
            "net_income_total": format(net_income_total, ".3f"),
        },
        "housekeeping": {
            "total_tasks": hk_qs.count(),
            "by_status": hk_by_status_map,
            "pending": hk_by_status_map.get(HousekeepingStatus.PENDING, 0),
            "in_progress": hk_by_status_map.get(HousekeepingStatus.IN_PROGRESS, 0),
            "done": hk_by_status_map.get(HousekeepingStatus.DONE, 0),
        },
        "maintenance": {
            "total_requests": m_qs.count(),
            "total_cost": format(maintenance_total_cost, ".3f"),
            "by_status": m_by_status_map,
            "open": m_by_status_map.get(MaintenanceStatus.OPEN, 0),
            "in_progress": m_by_status_map.get(MaintenanceStatus.IN_PROGRESS, 0),
            "resolved": m_by_status_map.get(MaintenanceStatus.RESOLVED, 0),
        },
    }
