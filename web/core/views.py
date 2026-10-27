from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
import logging
import mimetypes

from django import forms

from django.db import models, transaction, IntegrityError, connections
from django.core.paginator import Paginator
from django.conf import settings
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.http import FileResponse, HttpResponse, JsonResponse
from django.urls import reverse
from django.utils.http import urlencode
from django.utils.translation import gettext as _, get_language
from django.core.management import call_command
from tempfile import NamedTemporaryFile
import os
from io import StringIO

from bookings.models import Booking, BookingGroup, BookingStatus, BookingType, RentCycle, is_unit_available
from guests.models import Guest
from accounts.models import StaffProfile, StaffRole
from accounts.models import OwnerProfile
from inventory.models import Unit, UnitType, Amenity
from inventory.amenity_names import AMENITY_AR_NAMES
from maintenance.models import MaintenanceRequest, MaintenanceStatus, MaintenanceType
from housekeeping.models import HousekeepingTask, HousekeepingStatus
from billing.models import Invoice, Payment, InvoiceLine, InvoiceStatus, PaymentMethod, PaymentDirection
from pricing.models import RatePlan, SeasonalRateRule
from pricing.services import compute_booking_total
from settings_app.models import PropertyProfile, BusinessType
from settings_app.models import DatabaseConnection
from notifications.services import queue_event_message
from notifications.models import NotificationSetting, OutboxMessage, Channel
from contracts.models import Contract, ContractDocument
from inspections.models import MoveOutInspection
from sync_engine.models import SyncEvent, SyncInboundEvent, SyncEventStatus
from sync_engine.services import (
    get_or_create_sync_config,
    pull_remote_events,
    push_pending_events,
    reset_failed_events_for_retry,
    retry_dead_letters,
)

from .forms import (
    LoginForm,
    UnitForm,
    UnitTypeForm,
    GuestForm,
    GuestIdUploadForm,
    BookingForm,
    MaintenanceDraftForm,
    MaintenanceCompleteForm,
    InvoiceForm,
    PaymentForm,
    RatePlanForm,
    SeasonalRateRuleForm,
    ReportsForm,
    PropertyProfileForm,
    AmenityForm,
    StaffCreateForm,
    StaffEditForm,
    OwnerCreateForm,
    OwnerEditForm,
    DatabaseConnectionForm,
)
from guests.models import IDType

from .permissions import (
    ROLE_OWNER_ADMIN,
    ROLE_MANAGER,
    ROLE_RECEPTION,
    ROLE_HOUSEKEEPING,
    ROLE_MAINTENANCE,
    ROLES_ADMIN,
    ROLES_RECEPTION,
    ROLES_MAINTENANCE,
    ROLES_MAINTENANCE_VIEW,
    ROLES_HOUSEKEEPING,
    ROLES_HOUSEKEEPING_VIEW,
    ROLES_UNITS_MANAGE,
    ROLES_UNITS_VIEW,
    ROLES_BILLING,
    _get_user_role,
    _has_role,
    _require_roles,
    require_roles,
)

logger = logging.getLogger(__name__)



# =========================================================
# BOOKING WIZARD FORMS (kept in views.py to avoid touching forms.py)
# These are used by booking_wizard_step2.html and booking_wizard_step3.html templates.
# =========================================================

class BookingWizardStep2Form(forms.Form):
    units = forms.ModelMultipleChoiceField(queryset=Unit.objects.none(), required=True)

    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            if property_obj is not None:
                self.fields["units"].queryset = (
                    Unit.objects.filter(
                        property_profile=property_obj,
                        is_active=True,
                        unit_type__business_type=property_obj.business_type,
                    )
                    .select_related("unit_type")
                    .order_by("code")
                )
        except Exception:
            pass
        self.fields["units"].widget = forms.SelectMultiple(attrs={"class": "form-select", "size": "8"})


class BookingWizardGuestForm(forms.Form):
    existing_guest = forms.ModelChoiceField(queryset=Guest.objects.none(), required=False)

    full_name = forms.CharField(required=False, max_length=255)
    phone = forms.CharField(required=False, max_length=50)
    whatsapp = forms.CharField(required=False, max_length=50)
    email = forms.EmailField(required=False)
    nationality = forms.CharField(required=False, max_length=120)
    id_type = forms.ChoiceField(choices=IDType.choices, required=False)
    id_number = forms.CharField(required=False, max_length=80)
    address = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, property_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            if property_obj is not None:
                self.fields["existing_guest"].queryset = (
                    Guest.objects.filter(
                        property_profile=property_obj,
                        business_type=property_obj.business_type,
                        is_active=True,
                    )
                    .order_by("full_name")
                )
        except Exception:
            pass

        # Widgets / styling to match the Bootstrap-ish templates
        self.fields["existing_guest"].widget = forms.Select(attrs={"class": "form-select"})
        for f in ("full_name", "phone", "whatsapp", "nationality", "id_number"):
            self.fields[f].widget = forms.TextInput(attrs={"class": "form-control"})
        self.fields["id_type"].widget = forms.Select(attrs={"class": "form-select"})
        self.fields["email"].widget = forms.EmailInput(attrs={"class": "form-control"})
        self.fields["address"].widget.attrs.setdefault("class", "form-control")
        self.fields["notes"].widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        # If an existing guest is selected, we don't require any new-guest fields.
        if cleaned.get("existing_guest"):
            return cleaned

        # Otherwise, require at least full_name to create a new guest.
        name = (cleaned.get("full_name") or "").strip()
        if not name:
            self.add_error("full_name", "Full name is required if you are not selecting an existing guest.")
        else:
            cleaned["full_name"] = name
        return cleaned


def _get_active_property(request):
    pid = request.session.get("active_property_id")
    if pid:
        try:
            return PropertyProfile.objects.get(id=pid)
        except PropertyProfile.DoesNotExist:
            pass
    prop = PropertyProfile.objects.first()
    if prop:
        request.session["active_property_id"] = prop.id
    return prop


def _current_booking_type(prop):
    if not prop:
        return None
    return BookingType.HOTEL if getattr(prop, "business_type", "hotel") == "hotel" else BookingType.APARTMENT


def _is_desktop_qt_request(request) -> bool:
    user_agent = request.META.get("HTTP_USER_AGENT", "") or ""
    return "QtWebEngine" in user_agent or "QtWebEngineCore" in user_agent


def _is_admin_manager(user) -> bool:
    """Return True if the user is superuser or has Admin/Manager role."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return _has_role(user, ROLES_ADMIN)


def _can_manage_properties(user) -> bool:
    """Only Owner/Admin role (or superuser) can create/switch properties globally."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return _get_user_role(user) == ROLE_OWNER_ADMIN


def _filter_rateplans_for_mode(qs, prop):
    if not prop:
        return qs
    return qs.filter(
        models.Q(unit_type__business_type=prop.business_type)
        | models.Q(unit__unit_type__business_type=prop.business_type)
    )


def _filter_rules_for_mode(qs, prop):
    if not prop:
        return qs
    return qs.filter(
        models.Q(rate_plan__unit_type__business_type=prop.business_type)
        | models.Q(rate_plan__unit__unit_type__business_type=prop.business_type)
    )


def _filter_invoices_for_mode(qs, prop):
    if not prop:
        return qs
    booking_type = _current_booking_type(prop)
    if not booking_type:
        return qs
    return qs.filter(
        models.Q(booking__booking_type=booking_type)
        | models.Q(booking__isnull=True, guest__business_type=prop.business_type)
    )


def _filter_payments_for_mode(qs, prop):
    if not prop:
        return qs
    booking_type = _current_booking_type(prop)
    if not booking_type:
        return qs
    return qs.filter(
        models.Q(invoice__booking__booking_type=booking_type)
        | models.Q(invoice__booking__isnull=True, invoice__guest__business_type=prop.business_type)
    )


def _ensure_default_amenity_tiers(prop: PropertyProfile | None) -> None:
    if not prop:
        return
    defaults = ["Standard", "Deluxe", "Premium", "Luxury"]
    for name in defaults:
        try:
            obj, created = UnitType.objects.get_or_create(
                property_profile=prop,
                business_type=prop.business_type,
                name_en=name,
                defaults={
                    "business_type": prop.business_type,
                    "name_ar": "",
                    "base_rate": Decimal("0.000"),
                    "is_active": True,
                },
            )
        except IntegrityError:
            obj = UnitType.objects.filter(property_profile=prop, name_en=name).first()
            created = False
        # Do not overwrite business_type here; it would leak data across modes.


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    remember_cookie = request.COOKIES.get("slx_remember_username", "")
    if request.method == "POST":
        form = LoginForm(request.POST)
    else:
        form = LoginForm(
            initial={
                "username": remember_cookie,
                "remember": bool(remember_cookie),
            }
        )
    if request.method == "POST" and form.is_valid():
        user = authenticate(request, username=form.cleaned_data["username"], password=form.cleaned_data["password"])
        if user is None:
            messages.error(request, "Invalid username or password.")
        else:
            login(request, user)
            remember_me = bool(form.cleaned_data.get("remember"))
            if not remember_me:
                request.session.set_expiry(0)
            response = redirect("dashboard")
            if remember_me:
                response.set_cookie(
                    "slx_remember_username",
                    form.cleaned_data["username"],
                    max_age=60 * 60 * 24 * 30,
                    samesite="Lax",
                )
            else:
                response.delete_cookie("slx_remember_username")
            return response

    return render(request, "core/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard(request):
    owner_profile = getattr(request.user, "owner_profile", None)
    if owner_profile and owner_profile.is_active:
        return redirect("owner-home")

    prop = _get_active_property(request)

    qs_bookings = Booking.objects.select_related("unit", "guest").order_by("-created_at")
    qs_units = Unit.objects.all()
    qs_guests = Guest.objects.all()
    qs_rateplans = RatePlan.objects.all()
    qs_rules = SeasonalRateRule.objects.all()
    qs_maintenance = MaintenanceRequest.objects.all()
    qs_housekeeping = HousekeepingTask.objects.all()

    try:
        if prop:
            booking_type = _current_booking_type(prop)
            qs_bookings = qs_bookings.filter(property_profile=prop, booking_type=booking_type)
            qs_units = qs_units.filter(property_profile=prop, unit_type__business_type=prop.business_type)
            qs_guests = qs_guests.filter(property_profile=prop, business_type=prop.business_type)
            qs_rateplans = _filter_rateplans_for_mode(qs_rateplans.filter(property_profile=prop), prop)
            qs_rules = _filter_rules_for_mode(qs_rules.filter(property_profile=prop), prop)
            qs_maintenance = qs_maintenance.filter(property_profile=prop)
            qs_housekeeping = qs_housekeeping.filter(property_profile=prop)
    except Exception:
        pass

    bookings_active = qs_bookings.filter(is_archived=False).exclude(
        status__in=[BookingStatus.CANCELLED, BookingStatus.NO_SHOW]
    ).count()
    units = qs_units.count()
    occupancy_pct = int(round((bookings_active / units) * 100)) if units > 0 else 0
    occupancy_pct = max(0, min(100, occupancy_pct))

    stats = {
        "units": units,
        "guests": qs_guests.count(),
        "bookings_active": bookings_active,
        "rate_plans": qs_rateplans.filter(is_active=True).count() if hasattr(RatePlan, "is_active") else qs_rateplans.count(),
        "seasonal_rules": qs_rules.filter(is_active=True).count() if hasattr(SeasonalRateRule, "is_active") else qs_rules.count(),
        "maintenance_open": qs_maintenance.exclude(status__in=[MaintenanceStatus.RESOLVED, MaintenanceStatus.CANCELLED]).count(),
        "housekeeping_open": qs_housekeeping.exclude(status__in=[HousekeepingStatus.DONE, HousekeepingStatus.CANCELLED]).count(),
    }

    recent_bookings = list(qs_bookings[:6])
    today = timezone.localdate()
    month_start = today.replace(day=1)
    last_7_start = today - timedelta(days=6)
    prev_7_start = today - timedelta(days=13)
    prev_7_end = today - timedelta(days=7)

    qs_invoices = Invoice.objects.all()
    qs_payments = Payment.objects.all()
    if prop:
        qs_invoices = _filter_invoices_for_mode(qs_invoices.filter(property_profile=prop), prop)
        qs_payments = _filter_payments_for_mode(qs_payments.filter(property_profile=prop), prop)

    month_revenue = (
        qs_invoices.filter(issue_date__gte=month_start)
        .exclude(status=InvoiceStatus.VOID)
        .aggregate(v=models.Sum("total"))
        .get("v")
        or Decimal("0.000")
    )
    month_collections = (
        qs_payments.filter(created_at__date__gte=month_start, is_void=False, direction=PaymentDirection.IN)
        .aggregate(v=models.Sum("amount"))
        .get("v")
        or Decimal("0.000")
    )
    month_refunds = (
        qs_payments.filter(created_at__date__gte=month_start, is_void=False, direction=PaymentDirection.OUT)
        .aggregate(v=models.Sum("amount"))
        .get("v")
        or Decimal("0.000")
    )
    month_maintenance_cost = (
        qs_maintenance.filter(created_at__date__gte=month_start)
        .aggregate(v=models.Sum("total_cost"))
        .get("v")
        or Decimal("0.000")
    )
    net_income_month = month_revenue - month_maintenance_cost

    last_7_bookings = qs_bookings.filter(created_at__date__gte=last_7_start).count()
    prev_7_bookings = qs_bookings.filter(created_at__date__gte=prev_7_start, created_at__date__lte=prev_7_end).count()
    booking_trend_delta = last_7_bookings - prev_7_bookings

    analytics = {
        "month_revenue": month_revenue,
        "month_collections": month_collections,
        "month_refunds": month_refunds,
        "month_maintenance_cost": month_maintenance_cost,
        "net_income_month": net_income_month,
        "last_7_bookings": last_7_bookings,
        "prev_7_bookings": prev_7_bookings,
        "booking_trend_delta": booking_trend_delta,
    }

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    base = occupancy_pct or 30
    wave = [0, -8, -3, 6, -4, 10, 2]
    occupancy_bars = [{"day": d, "height": max(8, min(100, base + w))} for d, w in zip(days, wave)]

    return render(
        request,
        "core/dashboard.html",
        {
            "prop": prop,
            "stats": stats,
            "analytics": analytics,
            "recent_bookings": recent_bookings,
            "occupancy_pct": occupancy_pct,
            "occupancy_bars": occupancy_bars,
        },
    )


# =========================================================
# ROOMS / UNITS (CRUD)
# =========================================================
@require_roles(ROLES_UNITS_VIEW)
@login_required
def units_list(request):
    prop = _get_active_property(request)
    _ensure_default_amenity_tiers(prop)
    qs = Unit.objects.select_related("unit_type").prefetch_related(
        models.Prefetch(
            "unit_type__amenities",
            queryset=Amenity.objects.filter(property_profile=prop, is_active=True),
            to_attr="display_amenities",
        )
    ).order_by("code")
    if prop:
        qs = qs.filter(property_profile=prop, unit_type__business_type=prop.business_type)
    is_hotel = getattr(prop, "business_type", "hotel") == "hotel"
    mode_label = "Rooms" if is_hotel else "Units"
    mode_item_label = "Room" if is_hotel else "Unit"
    return render(request, "core/units_list.html", {"prop": prop, "units": qs, "mode_label": mode_label, "mode_item_label": mode_item_label})


@require_roles(ROLES_UNITS_MANAGE)
@login_required
def unit_create(request):
    prop = _get_active_property(request)
    _ensure_default_amenity_tiers(prop)
    form = UnitForm(request.POST or None, property_obj=prop)
    # Amenities are configured on the selected tier, not on the add form.
    form.fields.pop("amenities", None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.property_profile = prop
        obj.save()
        form.save_m2m()
        obj.amenities.set(obj.unit_type.amenities.filter(property_profile=prop, is_active=True))
        messages.success(request, _("Room/Unit created."))
        return redirect("units_list")
    label = _("Room") if getattr(prop, "business_type", "hotel") == "hotel" else _("Unit")
    title = _("Add %(label)s") % {"label": label}
    return render(request, "core/form_page.html", {"prop": prop, "title": title, "form": form, "back_url": "units_list", "mode_item_label": label})


@require_roles(ROLES_UNITS_MANAGE)
@login_required
def unit_edit(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(Unit, pk=pk, property_profile=prop)
    form = UnitForm(request.POST or None, instance=obj, property_obj=prop)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Room/Unit updated."))
        return redirect("units_list")
    label = _("Room") if getattr(prop, "business_type", "hotel") == "hotel" else _("Unit")
    title = _("Edit %(label)s #%(id)s") % {"label": label, "id": obj.id}
    return render(request, "core/form_page.html", {"prop": prop, "title": title, "form": form, "back_url": "units_list", "mode_item_label": label})


@require_roles(ROLES_UNITS_MANAGE)
@login_required
def unit_delete(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(Unit, pk=pk, property_profile=prop)
    if request.method == "POST":
        try:
            hk_qs = HousekeepingTask.objects.filter(unit=obj)
            if hk_qs.exists():
                active_hk = hk_qs.exclude(status__in=[HousekeepingStatus.DONE, HousekeepingStatus.CANCELLED])
                if active_hk.exists():
                    messages.error(request, _("Cannot delete this unit while it has active housekeeping tasks."))
                    return redirect("units_list")
                hk_qs.delete()
            obj.delete()
            messages.success(request, _("Room/Unit deleted."))
        except ProtectedError:
            messages.error(request, _("Cannot delete this unit because it has related records (e.g., housekeeping, bookings, or maintenance)."))
        return redirect("units_list")
    label = _("Room") if getattr(prop, "business_type", "hotel") == "hotel" else _("Unit")
    title = _("Delete %(label)s") % {"label": label}
    return render(request, "core/confirm_delete.html", {"prop": prop, "title": title, "object_label": str(obj), "back_url": "units_list", "mode_item_label": label})


# Unit Types (CRUD)
@require_roles(ROLES_UNITS_MANAGE)
@login_required
def unit_types_list(request):
    prop = _get_active_property(request)
    qs = UnitType.objects.order_by("name_en")
    if prop:
        qs = qs.filter(property_profile=prop, business_type=prop.business_type)
    mode_label = "Room Types" if getattr(prop, "business_type", "hotel") == "hotel" else "Unit Types"
    return render(request, "core/unit_types_list.html", {"prop": prop, "items": qs, "mode_label": mode_label})


@require_roles(ROLES_UNITS_MANAGE)
@login_required
def unit_type_create(request):
    prop = _get_active_property(request)
    form = UnitTypeForm(request.POST or None, property_obj=prop)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.property_profile = prop
        if prop:
            obj.business_type = prop.business_type
        obj.save()
        form.save_m2m()
        messages.success(request, "Room Type created.")
        return redirect("unit_types_list")
    label = "Room Type" if getattr(prop, "business_type", "hotel") == "hotel" else "Unit Type"
    return render(request, "core/form_page.html", {"prop": prop, "title": f"Add {label}", "form": form, "back_url": "unit_types_list"})


@require_roles(ROLES_UNITS_MANAGE)
@login_required
def unit_type_edit(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(UnitType, pk=pk, property_profile=prop)
    form = UnitTypeForm(request.POST or None, instance=obj, property_obj=prop)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Room Type updated.")
        return redirect("unit_types_list")
    label = "Room Type" if getattr(prop, "business_type", "hotel") == "hotel" else "Unit Type"
    return render(request, "core/form_page.html", {"prop": prop, "title": f"Edit {label} #{obj.id}", "form": form, "back_url": "unit_types_list"})


@require_roles(ROLES_UNITS_MANAGE)
@login_required
def unit_type_delete(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(UnitType, pk=pk, property_profile=prop)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Room Type deleted.")
        return redirect("unit_types_list")
    label = "Room Type" if getattr(prop, "business_type", "hotel") == "hotel" else "Unit Type"
    return render(request, "core/confirm_delete.html", {"prop": prop, "title": f"Delete {label}", "object_label": obj.name_en, "back_url": "unit_types_list"})


@require_roles(ROLES_UNITS_MANAGE)
@login_required
def unit_type_amenities(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(UnitType, pk=pk, property_profile=prop)
    if prop and obj.business_type != prop.business_type:
        return JsonResponse({"amenity_ids": []})
    amenity_ids = list(obj.amenities.values_list("id", flat=True))
    return JsonResponse({"amenity_ids": amenity_ids})


# =========================================================
# BOOKINGS (CRUD + existing actions)
# =========================================================
@require_roles(ROLES_RECEPTION)
@login_required
def bookings_list(request):
    prop = _get_active_property(request)
    include_archived = request.GET.get("include_archived") == "1"
    is_hotel = getattr(prop, "business_type", "hotel") == "hotel"
    booking_type = BookingType.HOTEL if is_hotel else BookingType.APARTMENT

    qs = Booking.objects.select_related("unit", "guest").order_by("-created_at")
    if prop:
        qs = qs.filter(property_profile=prop, booking_type=booking_type)
    if not include_archived:
        qs = qs.filter(is_archived=False)

    status_q = (request.GET.get("status") or "").strip()
    guest_q = (request.GET.get("guest") or "").strip()
    unit_q = (request.GET.get("unit") or "").strip()
    start_q = (request.GET.get("start_date") or "").strip()
    end_q = (request.GET.get("end_date") or "").strip()

    if status_q:
        qs = qs.filter(status=status_q)
    if guest_q:
        qs = qs.filter(guest__full_name__icontains=guest_q)
    if unit_q:
        qs = qs.filter(unit__code__icontains=unit_q)
    if start_q:
        try:
            qs = qs.filter(start_date__gte=date.fromisoformat(start_q))
        except Exception:
            pass
    if end_q:
        try:
            qs = qs.filter(end_date__lte=date.fromisoformat(end_q))
        except Exception:
            pass

    # Mark bookings created from mobile app so reception can identify source quickly.
    try:
        from mobile_api.bookings.models import MobilePaymentRecord

        mobile_source_subq = MobilePaymentRecord.objects.filter(booking_id=models.OuterRef("id"))
        qs = qs.annotate(is_mobile_source=models.Exists(mobile_source_subq))
    except Exception:
        qs = qs.annotate(is_mobile_source=models.Value(False, output_field=models.BooleanField()))

    active_statuses = [BookingStatus.RESERVED, BookingStatus.CHECKED_IN]
    active_bookings = qs.filter(status__in=active_statuses)
    past_bookings = qs.exclude(status__in=active_statuses)

    can_manage = bool(request.user.is_superuser or _has_role(request.user, ROLES_ADMIN))

    return render(
        request,
        "core/bookings_list.html",
        {
            "prop": prop,
            "active_bookings": active_bookings[:500],
            "past_bookings": past_bookings[:500],
            "include_archived": include_archived,
            "is_hotel": is_hotel,
            "can_manage": can_manage,
            "filters": {"status": status_q, "guest": guest_q, "unit": unit_q, "start_date": start_q, "end_date": end_q},
        },
    )


@require_roles(ROLES_RECEPTION)
@login_required
def booking_create(request):
    prop = _get_active_property(request)
    form = BookingForm(request.POST or None, property_obj=prop)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.property_profile = prop
        obj.save()
        messages.success(request, "Booking created.")
        return redirect("bookings_list")
    return render(request, "core/form_page.html", {"prop": prop, "title": "Create Booking", "form": form, "back_url": "bookings_list"})


@require_roles(ROLES_RECEPTION)
@login_required
def booking_edit(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(Booking, pk=pk, property_profile=prop)
    form = BookingForm(request.POST or None, instance=obj, property_obj=prop)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Booking updated.")
        return redirect("bookings_list")
    return render(request, "core/form_page.html", {"prop": prop, "title": f"Edit Booking #{obj.id}", "form": form, "back_url": "bookings_list"})


@require_roles(ROLES_RECEPTION)
@login_required
def booking_delete(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(Booking, pk=pk, property_profile=prop)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Booking deleted.")
        return redirect("bookings_list")
    return render(request, "core/confirm_delete.html", {"prop": prop, "title": "Delete Booking", "object_label": f"Booking #{obj.id}", "back_url": "bookings_list"})


@require_roles(ROLES_RECEPTION)
@login_required
def booking_action(request, pk: int):
    prop = _get_active_property(request)
    booking = get_object_or_404(Booking, pk=pk, property_profile=prop)

    if request.method != "POST":
        return redirect("bookings_list")

    action = request.POST.get("action")

    def _ensure_checkout_housekeeping_task() -> None:
        if HousekeepingTask.objects.filter(
            property_profile=prop,
            unit=booking.unit,
            status__in=[HousekeepingStatus.PENDING, HousekeepingStatus.IN_PROGRESS],
        ).exists():
            return
        HousekeepingTask.objects.create(
            property_profile=prop,
            unit=booking.unit,
            booking=booking,
            status=HousekeepingStatus.PENDING,
            title=f"Checkout cleaning for {booking.unit.code}",
        )
    try:
        if action == "check_in":
            booking.status = BookingStatus.CHECKED_IN
            booking.save(update_fields=["status", "updated_at"])
            try:
                from inventory.models import UnitStatus
                booking.unit.status = UnitStatus.OCCUPIED
                booking.unit.save(update_fields=["status", "updated_at"])
            except Exception:
                pass
            messages.success(request, "Checked in.")

        elif action == "check_out":
            checkout_date = timezone.localdate()
            if booking.end_date and booking.end_date > checkout_date:
                booking.end_date = checkout_date
            booking.status = BookingStatus.CHECKED_OUT
            booking.save(update_fields=["status", "end_date", "updated_at"])
            if booking.booking_group_id:
                group = booking.booking_group
                if group and group.end_date and group.end_date > checkout_date:
                    group.end_date = checkout_date
                    group.save(update_fields=["end_date", "updated_at"])
            try:
                from inventory.models import UnitStatus
                booking.unit.status = UnitStatus.HOUSEKEEPING
                booking.unit.save(update_fields=["status", "updated_at"])
            except Exception:
                pass
            _ensure_checkout_housekeeping_task()
            messages.success(request, "Checked out.")

        elif action == "cancel":
            booking.status = BookingStatus.CANCELLED
            booking.save(update_fields=["status", "updated_at"])
            messages.success(request, "Cancelled.")

        elif action == "no_show":
            booking.status = BookingStatus.NO_SHOW
            booking.save(update_fields=["status", "updated_at"])
            messages.success(request, "Marked as no-show.")

        elif action == "archive":
            booking.is_archived = True
            booking.save(update_fields=["is_archived", "updated_at"])
            messages.success(request, "Archived.")
        else:
            messages.error(request, "Unknown action.")
    except Exception as e:
        messages.error(request, f"Action failed: {e}")

    return redirect("bookings_list")


def _booking_currency(prop: PropertyProfile | None) -> str:
    if prop and getattr(prop, "currency", None):
        return prop.currency
    return "OMR"


def _booking_checkout_summary(booking: Booking) -> dict:
    inv = Invoice.objects.filter(booking=booking).order_by("-created_at").first()
    if inv:
        total = inv.total
        advance = inv.amount_paid
        balance = inv.balance_due
        currency = inv.currency or _booking_currency(booking.property_profile)
        return {
            "invoice": inv,
            "total": total,
            "advance": advance,
            "balance": balance,
            "currency": currency,
        }

    nights = max((booking.end_date - booking.start_date).days, 1)
    total = (booking.rate * Decimal(nights)) - (booking.discount or Decimal("0.000"))
    if total < Decimal("0.000"):
        total = Decimal("0.000")
    advance = booking.deposit or Decimal("0.000")
    balance = total - advance
    currency = _booking_currency(booking.property_profile)

    return {
        "invoice": None,
        "total": total.quantize(Decimal("0.001")),
        "advance": advance.quantize(Decimal("0.001")),
        "balance": balance.quantize(Decimal("0.001")),
        "currency": currency,
    }


def _ensure_booking_invoice(booking: Booking) -> Invoice:
    inv = Invoice.objects.filter(booking=booking).order_by("-created_at").first()
    if inv:
        inv.ensure_invoice_no()
        return inv

    currency = _booking_currency(booking.property_profile)
    inv = Invoice.objects.create(
        property_profile=booking.property_profile,
        booking=booking,
        guest=booking.guest,
        status=InvoiceStatus.ISSUED,
        issue_date=timezone.localdate(),
        currency=currency,
        notes=f"Auto-generated at checkout for booking #{booking.id}",
    )
    inv.ensure_invoice_no()

    nights = max((booking.end_date - booking.start_date).days, 1)
    line = InvoiceLine.objects.create(
        invoice=inv,
        description=f"Accommodation {booking.unit.code} ({booking.start_date} -> {booking.end_date})",
        quantity=Decimal(nights),
        unit_price=booking.rate,
        discount_amount=booking.discount or Decimal("0.000"),
        tax_rate=Decimal("0.000"),
    )
    line.recalc_tax()
    line.save(update_fields=["tax_amount"])

    if booking.deposit and booking.deposit > Decimal("0.000"):
        Payment.objects.create(
            invoice=inv,
            property_profile=booking.property_profile,
            method=PaymentMethod.OTHER,
            direction=PaymentDirection.IN,
            amount=booking.deposit,
            reference="Advance",
            paid_at=timezone.now(),
        )

    inv.recalc_and_save()
    return inv


@require_roles(ROLES_RECEPTION)
@login_required
def booking_checkout_info(request, pk: int):
    prop = _get_active_property(request)
    booking = get_object_or_404(Booking.objects.select_related("guest", "unit"), pk=pk, property_profile=prop)
    summary = _booking_checkout_summary(booking)
    inv: Invoice | None = summary["invoice"]

    payload = {
        "booking_id": booking.id,
        "guest": booking.guest.full_name,
        "unit": booking.unit.code,
        "check_in": booking.start_date.isoformat(),
        "check_out": booking.end_date.isoformat(),
        "total": str(summary["total"]),
        "advance": str(summary["advance"]),
        "balance": str(summary["balance"]),
        "currency": summary["currency"],
        "invoice_id": inv.id if inv else None,
        "invoice_no": inv.invoice_no if inv else "",
    }
    if inv:
        lang_code = (getattr(request, "LANGUAGE_CODE", "en") or "en")[:2]
        payload["print_url"] = f"{reverse('invoice_print', args=[inv.id])}?lang={lang_code}&doc=receipt"
    return JsonResponse(payload)


@require_roles(ROLES_RECEPTION)
@login_required
def booking_checkout_invoice(request, pk: int):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required."}, status=405)

    prop = _get_active_property(request)
    booking = get_object_or_404(Booking.objects.select_related("guest", "unit"), pk=pk, property_profile=prop)
    inv = _ensure_booking_invoice(booking)

    lang_code = (getattr(request, "LANGUAGE_CODE", "en") or "en")[:2]
    return JsonResponse(
        {
            "ok": True,
            "invoice_id": inv.id,
            "invoice_no": inv.invoice_no,
            "print_url": f"{reverse('invoice_print', args=[inv.id])}?lang={lang_code}&doc=receipt",
        }
    )


@require_roles(ROLES_RECEPTION)
@login_required
def booking_checkout_whatsapp(request, pk: int):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required."}, status=405)

    prop = _get_active_property(request)
    booking = get_object_or_404(Booking.objects.select_related("guest", "unit"), pk=pk, property_profile=prop)
    inv = _ensure_booking_invoice(booking)

    queue_event_message(
        property_profile=inv.property_profile,
        event_key="payment_received",
        to_phone=(inv.guest.whatsapp or inv.guest.phone),
        context={
            "guest_name": inv.guest.full_name,
            "invoice_no": inv.invoice_no,
            "paid_amount": str(inv.amount_paid),
            "balance": str(inv.balance_due),
        },
    )

    return JsonResponse({"ok": True})


@require_roles(ROLES_RECEPTION)
@login_required
def booking_checkout(request, pk: int):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required."}, status=405)

    prop = _get_active_property(request)
    booking = get_object_or_404(Booking.objects.select_related("guest", "unit"), pk=pk, property_profile=prop)
    inv = _ensure_booking_invoice(booking)

    amount_raw = (request.POST.get("amount") or "0").strip()
    method = (request.POST.get("method") or PaymentMethod.CASH).strip()
    reference = (request.POST.get("reference") or "").strip()

    try:
        amount = Decimal(amount_raw or "0")
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid amount."}, status=400)

    inv.recalc_and_save()

    if inv.balance_due > Decimal("0.000") and amount < inv.balance_due:
        return JsonResponse({"ok": False, "error": "Remaining balance must be collected before checkout."}, status=400)

    if amount > Decimal("0.000"):
        Payment.objects.create(
            invoice=inv,
            property_profile=booking.property_profile,
            method=method if method in PaymentMethod.values else PaymentMethod.CASH,
            direction=PaymentDirection.IN,
            amount=amount,
            reference=reference,
            paid_at=timezone.now(),
        )

    inv.recalc_and_save()

    checkout_date = timezone.localdate()
    if booking.end_date and booking.end_date > checkout_date:
        booking.end_date = checkout_date
    booking.status = BookingStatus.CHECKED_OUT
    booking.save(update_fields=["status", "end_date", "updated_at"])
    if booking.booking_group_id:
        group = booking.booking_group
        if group and group.end_date and group.end_date > checkout_date:
            group.end_date = checkout_date
            group.save(update_fields=["end_date", "updated_at"])
    try:
        from inventory.models import UnitStatus

        booking.unit.status = UnitStatus.HOUSEKEEPING
        booking.unit.save(update_fields=["status", "updated_at"])
    except Exception:
        pass

    if not HousekeepingTask.objects.filter(
        property_profile=prop,
        unit=booking.unit,
        status__in=[HousekeepingStatus.PENDING, HousekeepingStatus.IN_PROGRESS],
    ).exists():
        HousekeepingTask.objects.create(
            property_profile=prop,
            unit=booking.unit,
            booking=booking,
            status=HousekeepingStatus.PENDING,
            title=f"Checkout cleaning for {booking.unit.code}",
        )

    lang_code = (getattr(request, "LANGUAGE_CODE", "en") or "en")[:2]
    return JsonResponse(
        {
            "ok": True,
            "invoice_id": inv.id,
            "invoice_no": inv.invoice_no,
            "print_url": f"{reverse('invoice_print', args=[inv.id])}?lang={lang_code}&doc=receipt",
        }
    )



# =========================================================
# BOOKINGS - WIZARD (4-step create)
# Session-backed state, inspired by desktop booking_window.py
# =========================================================

_WIZ_SESSION_KEY = "booking_wizard_state"


def _wiz_get(request) -> dict:
    return dict(request.session.get(_WIZ_SESSION_KEY) or {})


def _wiz_set(request, data: dict) -> None:
    request.session[_WIZ_SESSION_KEY] = data
    request.session.modified = True


def _wiz_clear(request) -> None:
    if _WIZ_SESSION_KEY in request.session:
        del request.session[_WIZ_SESSION_KEY]
        request.session.modified = True


@require_roles(ROLES_RECEPTION)
@login_required
def booking_wizard_start(request):
    """
    Start a fresh wizard session and go to step 1.
    """
    _wiz_clear(request)
    prop = _get_active_property(request)
    rent_cycle = request.GET.get("rent_cycle") or ""
    is_hotel = getattr(prop, "business_type", "hotel") == "hotel"
    booking_type = BookingType.HOTEL if is_hotel else BookingType.APARTMENT
    if rent_cycle not in {RentCycle.NIGHTLY, RentCycle.MONTHLY}:
        rent_cycle = RentCycle.NIGHTLY if is_hotel else RentCycle.MONTHLY
    _wiz_set(request, {"step": 1, "booking_type": booking_type, "rent_cycle": rent_cycle})
    return redirect("booking_wizard_step1")


@require_roles(ROLES_RECEPTION)
@login_required
def booking_wizard_cancel(request):
    state = _wiz_get(request)
    prop = _get_active_property(request)
    created_booking_ids = state.get("created_booking_ids") or []
    created_group_id = state.get("created_group_id")
    created_invoice_id = state.get("created_invoice_id")

    if prop and (created_booking_ids or created_group_id or created_invoice_id):
        try:
            with transaction.atomic():
                if created_invoice_id:
                    Invoice.objects.filter(id=created_invoice_id, property_profile=prop).delete()
                if created_booking_ids:
                    Booking.objects.filter(id__in=created_booking_ids, property_profile=prop).delete()
                if created_group_id:
                    BookingGroup.objects.filter(id=created_group_id, property_profile=prop).delete()
            messages.info(request, "Booking wizard cancelled and temporary records were removed.")
        except Exception:
            logger.exception("Failed to rollback wizard-created records on cancel")
            messages.warning(
                request,
                "Wizard cancelled, but some created records could not be auto-removed. Please review bookings list.",
            )
    _wiz_clear(request)
    if not (created_booking_ids or created_group_id or created_invoice_id):
        messages.info(request, "Booking wizard cancelled.")
    return redirect("bookings_list")


def _wiz_require_prop(prop):
    if not prop:
        raise ValueError("No active property configured. Please create/select a property profile first.")


def _wiz_parse_date(s: str) -> date:
    # Django form-less date parsing
    return date.fromisoformat(s)



@login_required
@require_roles(ROLES_RECEPTION)
def booking_wizard_step1(request):
    """
    Step 1: Dates + guests counts + booking type + rent cycle.
    """
    prop = _get_active_property(request)
    try:
        _wiz_require_prop(prop)
    except Exception as e:
        messages.error(request, str(e))
        return redirect("settings_page")

    state = _wiz_get(request)

    if request.method == "POST":
        try:
            start_date = _wiz_parse_date(request.POST.get("start_date", ""))
            end_date = _wiz_parse_date(request.POST.get("end_date", ""))
        except Exception:
            messages.error(request, "Please enter valid check-in and check-out dates.")
            return render(request, "core/booking_wizard_step1.html", {"prop": prop, "step": 1, "state": state})

        if end_date <= start_date:
            messages.error(request, "Check-out must be after check-in.")
            return render(request, "core/booking_wizard_step1.html", {"prop": prop, "step": 1, "state": state})

        is_hotel = getattr(prop, "business_type", "hotel") == "hotel"
        booking_type = BookingType.HOTEL if is_hotel else BookingType.APARTMENT
        rent_cycle = state.get("rent_cycle") or (RentCycle.NIGHTLY if is_hotel else RentCycle.MONTHLY)

        try:
            adults = int(request.POST.get("adults") or 1)
            children = int(request.POST.get("children") or 0)
        except Exception:
            messages.error(request, "Please enter valid adults/children values.")
            return render(request, "core/booking_wizard_step1.html", {"prop": prop, "step": 1, "state": state})

        if adults < 1 or children < 0:
            messages.error(request, "Adults must be at least 1, and children cannot be negative.")
            return render(request, "core/booking_wizard_step1.html", {"prop": prop, "step": 1, "state": state})

        state.update(
            {
                "step": 1,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "booking_type": booking_type,
                "rent_cycle": rent_cycle,
                "adults": adults,
                "children": children,
            }
        )
        _wiz_set(request, state)
        return redirect("booking_wizard_step2")

    return render(request, "core/booking_wizard_step1.html", {"prop": prop, "step": 1, "state": state})


@login_required
@require_roles(ROLES_RECEPTION)
def booking_wizard_step2(request):
    """
    Step 2: Show availability list and choose ONE unit (StayLux Booking model has FK to Unit).
    Template uses {{ form.unit }}.
    """
    prop = _get_active_property(request)
    try:
        _wiz_require_prop(prop)
    except Exception as e:
        messages.error(request, str(e))
        return redirect("settings_page")

    state = _wiz_get(request)
    if not state.get("start_date") or not state.get("end_date"):
        messages.info(request, "Please complete Step 1 first.")
        return redirect("booking_wizard_step1")

    check_in = _wiz_parse_date(state["start_date"])
    check_out = _wiz_parse_date(state["end_date"])
    # Build rows for the table (price preview + availability badge)
    units_qs = (
        Unit.objects.filter(
            property_profile=prop,
            is_active=True,
            unit_type__business_type=prop.business_type,
        )
        .select_related("unit_type")
        .order_by("code")
    )
    rows = []
    for u in units_qs:
        available = is_unit_available(u.id, check_in, check_out)
        if not available:
            continue
        rent_cycle = state.get("rent_cycle") or RentCycle.NIGHTLY
        nights = max((check_out - check_in).days, 1)
        if rent_cycle == RentCycle.MONTHLY:
            total = (u.monthly_price or Decimal("0.000"))
        else:
            total = (u.daily_price or Decimal("0.000")) * Decimal(nights)
        rows.append({"unit": u, "available": available, "total": total, "currency": "OMR", "nights": nights})

    if request.method == "POST":
        unit_ids = request.POST.getlist("units")
        units = list(
            Unit.objects.filter(
                property_profile=prop,
                is_active=True,
                id__in=unit_ids,
                unit_type__business_type=prop.business_type,
            ).select_related("unit_type")
        )
        if not units:
            messages.error(request, "Please select at least one unit.")
            return redirect("booking_wizard_step2")

        for unit in units:
            if not is_unit_available(unit.id, check_in, check_out):
                messages.error(request, "One of the selected units is no longer available. Please choose again.")
                return redirect("booking_wizard_step2")

        state.update({"step": 2, "unit_ids": [u.id for u in units]})
        _wiz_set(request, state)
        return redirect("booking_wizard_step3")

    return render(
        request,
        "core/booking_wizard_step2.html",
        {"prop": prop, "step": 2, "state": state, "rows": rows, "check_in": check_in, "check_out": check_out},
    )


@require_roles(ROLES_RECEPTION)
@login_required
def booking_wizard_step3(request):
    """
    Step 3: Select existing guest OR create a new guest.
    Template uses {{ form.existing_guest }} + new guest fields.
    """
    prop = _get_active_property(request)
    try:
        _wiz_require_prop(prop)
    except Exception as e:
        messages.error(request, str(e))
        return redirect("settings_page")

    state = _wiz_get(request)
    if not state.get("unit_ids"):
        messages.info(request, "Please complete Step 2 first.")
        return redirect("booking_wizard_step2")

    form = BookingWizardGuestForm(request.POST or None, property_obj=prop)
    existing_guests = list(form.fields["existing_guest"].queryset) if "existing_guest" in form.fields else []

    if request.method == "POST":
        if not form.is_valid():
            return render(
                request,
                "core/booking_wizard_step3.html",
                {"prop": prop, "step": 3, "state": state, "form": form, "existing_guests": existing_guests},
            )

        existing = form.cleaned_data.get("existing_guest")
        if existing:
            state.update({"step": 3, "guest_id": existing.id})
            _wiz_set(request, state)
            return redirect("booking_wizard_step4")

        # Create new guest
        g = Guest(
            property_profile=prop,
            business_type=prop.business_type,
            full_name=form.cleaned_data.get("full_name") or "",
            phone=form.cleaned_data.get("phone") or "",
            whatsapp=form.cleaned_data.get("whatsapp") or "",
            email=form.cleaned_data.get("email") or "",
            nationality=form.cleaned_data.get("nationality") or "",
            id_type=(form.cleaned_data.get("id_type") or "") or None,
            id_number=form.cleaned_data.get("id_number") or "",
            address=form.cleaned_data.get("address") or "",
            notes=form.cleaned_data.get("notes") or "",
        )
        try:
            g.full_clean()
        except Exception as e:
            messages.error(request, f"Guest details error: {e}")
            return render(
                request,
                "core/booking_wizard_step3.html",
                {"prop": prop, "step": 3, "state": state, "form": form, "existing_guests": existing_guests},
            )

        g.save()
        state.update({"step": 3, "guest_id": g.id})
        _wiz_set(request, state)
        return redirect("booking_wizard_step4")

    return render(
        request,
        "core/booking_wizard_step3.html",
        {"prop": prop, "step": 3, "state": state, "form": form, "existing_guests": existing_guests},
    )


@require_roles(ROLES_RECEPTION)
@login_required
def booking_wizard_step4(request):
    """
    Step 4: Payment + Confirm -> create Booking + Invoice + optional Payment.
    """
    prop = _get_active_property(request)
    try:
        _wiz_require_prop(prop)
    except Exception as e:
        messages.error(request, str(e))
        return redirect("settings_page")

    state = _wiz_get(request)
    missing = [k for k in ("start_date", "end_date", "unit_ids", "guest_id") if not state.get(k)]
    if missing:
        messages.info(request, "Please complete previous steps first.")
        return redirect("booking_wizard_step1")

    check_in = _wiz_parse_date(state["start_date"])
    check_out = _wiz_parse_date(state["end_date"])
    nights = (check_out - check_in).days
    created_booking_ids = state.get("created_booking_ids") or []
    created_bookings = []
    if created_booking_ids:
        created_bookings = list(
            Booking.objects.select_related("unit", "unit__unit_type").filter(
                id__in=created_booking_ids,
                property_profile=prop,
            )
        )

    if created_bookings:
        units = [b.unit for b in created_bookings]
    else:
        units = list(
            Unit.objects.select_related("unit_type").filter(
                id__in=state["unit_ids"],
                property_profile=prop,
                unit_type__business_type=prop.business_type,
            )
        )
    guest = get_object_or_404(Guest, id=state["guest_id"], property_profile=prop)

    if not units:
        messages.error(request, "No valid units selected.")
        return redirect("booking_wizard_step2")

    # Re-check availability (race condition protection)
    if not created_bookings:
        for unit in units:
            if not is_unit_available(unit.id, check_in, check_out):
                messages.error(request, "One of the selected units is no longer available. Please choose again.")
                return redirect("booking_wizard_step2")

    rent_cycle = state.get("rent_cycle") or RentCycle.NIGHTLY
    currency = "OMR"
    base_total = Decimal("0.000")
    unit_rows = []
    if created_bookings:
        for booking in created_bookings:
            unit = booking.unit
            rate = booking.locked_rate if booking.price_locked else booking.rate
            if rent_cycle == RentCycle.MONTHLY:
                total = rate
            else:
                total = rate * Decimal(max(nights, 1))
            base_total += total
            unit_rows.append({"unit": unit, "total": total, "rate": rate})
    else:
        for unit in units:
            if rent_cycle == RentCycle.MONTHLY:
                total = unit.monthly_price or Decimal("0.000")
                rate = unit.monthly_price or Decimal("0.000")
            else:
                total = (unit.daily_price or Decimal("0.000")) * Decimal(max(nights, 1))
                rate = unit.daily_price or Decimal("0.000")
            base_total += total
            unit_rows.append({"unit": unit, "total": total, "rate": rate})

    # Defaults for UI
    summary = {
        "units": unit_rows,
        "guest": guest,
        "check_in": check_in,
        "check_out": check_out,
        "nights": nights,
        "currency": currency,
        "base_total": base_total,
        "final_total": base_total,
        "balance": base_total,
    }

    if request.method != "POST":
        if request.GET.get("from_print") == "1":
            list(messages.get_messages(request))
        return render(request, "core/booking_wizard_step4.html", {"prop": prop, "step": 4, "state": state, "summary": summary, "payment_methods": PaymentMethod.choices})

    if request.method == "POST":
        # monetary fields
        try:
            discount = Decimal((request.POST.get("discount") or "0").strip() or "0")
            advance = Decimal((request.POST.get("advance_payment") or "0").strip() or "0")
        except Exception:
            messages.error(request, "Enter valid numbers for discount/advance payment.")
            return render(request, "core/booking_wizard_step4.html", {"prop": prop, "step": 4, "state": state, "summary": summary, "payment_methods": PaymentMethod.choices})

        if discount < 0 or advance < 0:
            messages.error(request, "Discount and advance payment cannot be negative.")
            return render(request, "core/booking_wizard_step4.html", {"prop": prop, "step": 4, "state": state, "summary": summary, "payment_methods": PaymentMethod.choices})

        final_total = base_total - discount
        if final_total < Decimal("0.000"):
            final_total = Decimal("0.000")

        balance = final_total - advance
        if balance < Decimal("0.000"):
            balance = Decimal("0.000")

        method = request.POST.get("payment_method") or PaymentMethod.CASH
        notes = (request.POST.get("notes") or "").strip()

        summary.update({"final_total": final_total, "balance": balance})

        created_inv_id = state.get("created_invoice_id")
        created_group_id = state.get("created_group_id")
        created_booking_ids = state.get("created_booking_ids") or []
        action = request.POST.get("action") or "finish"
        open_new_tab = request.POST.get("open_new_tab") == "1"
        lang_code = (getattr(request, "LANGUAGE_CODE", "en") or "en")[:2]

        inv = None
        group = None
        if created_inv_id and created_group_id and created_booking_ids:
            inv = Invoice.objects.filter(id=created_inv_id, property_profile=prop).first()
            group = BookingGroup.objects.filter(id=created_group_id, property_profile=prop).first()
            if not inv or not group:
                inv = None
                group = None
                created_booking_ids = []

        if not inv or not group:
            try:
                from bookings.services import create_booking_group_and_bookings

                # Service layer expects real date objects, while wizard session
                # keeps ISO strings.
                service_state = dict(state)
                service_state["start_date"] = check_in
                service_state["end_date"] = check_out

                created_group, created_bookings, inv = create_booking_group_and_bookings(
                    property_profile=prop,
                    guest=guest,
                    unit_rows=unit_rows,
                    state=service_state,
                    rent_cycle=rent_cycle,
                    booking_type=state.get("booking_type") or BookingType.HOTEL,
                    discount=discount,
                    advance=advance,
                    payment_method=method,
                    notes=notes,
                )
                group = created_group
                booking_ids = [b.id for b in created_bookings]
                state.update(
                    {
                        "created_invoice_id": inv.id,
                        "created_group_id": created_group.id,
                        "created_booking_ids": booking_ids,
                    }
                )
                _wiz_set(request, state)
                if action == "finish":
                    messages.success(request, "Booking created successfully.")

            except Exception as e:
                logger.exception("Booking wizard step4 failed during create_booking_group_and_bookings")
                messages.error(request, f"Failed to create booking: {e}")
                return render(request, "core/booking_wizard_step4.html", {"prop": prop, "step": 4, "state": state, "summary": summary, "payment_methods": PaymentMethod.choices})

        user_agent = request.META.get("HTTP_USER_AGENT", "") or ""
        is_desktop_qt = "QtWebEngine" in user_agent or "QtWebEngineCore" in user_agent

        def _open_new_tab_and_redirect(open_url: str):
            target_url = reverse("bookings_list")
            html = (
                "<html><body>"
                f"<script>window.open('{open_url}', '_blank'); window.location.href='{target_url}';</script>"
                "</body></html>"
            )
            return HttpResponse(html)

        back_url = f"{reverse('booking_wizard_step4')}?from_print=1"
        back_qs = urlencode({"back": back_url})
        if action == "print_receipt":
            receipt_url = f"/billing/invoices/{inv.id}/print/?lang={lang_code}&doc=receipt&{back_qs}"
            if is_desktop_qt:
                return redirect(receipt_url)
            return redirect(receipt_url) if open_new_tab else _open_new_tab_and_redirect(receipt_url)
        if action == "save_pdf":
            receipt_url = f"/billing/invoices/{inv.id}/print/?download=1&lang={lang_code}&doc=receipt&{back_qs}"
            if is_desktop_qt:
                return redirect(receipt_url)
            return redirect(receipt_url) if open_new_tab else _open_new_tab_and_redirect(receipt_url)
        if action in {"print_agreement", "save_agreement"}:
            if prop and prop.business_type == BusinessType.APARTMENTS and rent_cycle == RentCycle.MONTHLY:
                if not group:
                    messages.error(request, "Agreement record is not available yet. Please try again.")
                    return redirect("bookings_list")
                if action == "print_agreement":
                    agreement_url = f"/bookings/group/{group.id}/agreement/?lang={lang_code}&{back_qs}"
                else:
                    agreement_url = f"/bookings/group/{group.id}/agreement/?download=1&lang={lang_code}&{back_qs}"
                if is_desktop_qt:
                    return redirect(agreement_url)
                return redirect(agreement_url) if open_new_tab else _open_new_tab_and_redirect(agreement_url)
            messages.error(request, "Agreement is available for monthly apartments only.")
            return redirect("bookings_list")
        if action == "whatsapp":
            phone = (guest.whatsapp or guest.phone or "").replace("+", "")
            msg = f"Booking confirmed for {guest.full_name}. Dates: {check_in} to {check_out}. Total: {summary['final_total']} {currency}."
            return redirect(f"https://wa.me/{phone}?{urlencode({'text': msg})}")
        _wiz_clear(request)
        return redirect("bookings_list")

    return render(request, "core/booking_wizard_step4.html", {"prop": prop, "step": 4, "state": state, "summary": summary, "payment_methods": PaymentMethod.choices})


# =========================================================
# GUESTS (CRUD)
# =========================================================
@require_roles(ROLES_RECEPTION)
@login_required
def guests_list(request):
    prop = _get_active_property(request)
    is_hotel = getattr(prop, "business_type", "hotel") == "hotel"
    booking_type = BookingType.HOTEL if is_hotel else BookingType.APARTMENT
    qs = Guest.objects.order_by("-created_at")
    if prop:
        qs = qs.filter(property_profile=prop, business_type=prop.business_type)

    q = (request.GET.get("q") or "").strip()
    id_q = (request.GET.get("id_number") or "").strip()
    phone_q = (request.GET.get("phone") or "").strip()

    if q:
        qs = qs.filter(full_name__icontains=q)
    if id_q:
        qs = qs.filter(id_number__icontains=id_q)
    if phone_q:
        qs = qs.filter(phone__icontains=phone_q)

    guests = list(qs[:500])
    guest_ids = [g.id for g in guests]
    last_bookings = {}
    if guest_ids:
        bookings_qs = Booking.objects.filter(guest_id__in=guest_ids, booking_type=booking_type).order_by("guest_id", "-start_date")
        for b in bookings_qs:
            if b.guest_id not in last_bookings:
                last_bookings[b.guest_id] = b

    for g in guests:
        lb = last_bookings.get(g.id)
        g.last_check_in = lb.start_date if lb else None
        g.last_check_out = lb.end_date if lb else None

    can_manage = bool(request.user.is_superuser or _has_role(request.user, ROLES_ADMIN))

    return render(
        request,
        "core/guests_list.html",
        {
            "prop": prop,
            "guests": guests,
            "filters": {"q": q, "id_number": id_q, "phone": phone_q},
            "can_manage": can_manage,
        },
    )


@require_roles(ROLES_RECEPTION)
@login_required
def guest_id_upload(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(Guest, pk=pk, property_profile=prop)
    form = GuestIdUploadForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Guest ID uploaded.")
        return redirect("guests_list")
    return render(
        request,
        "core/form_page.html",
        {
            "prop": prop,
            "title": f"Upload ID for {obj.full_name}",
            "form": form,
            "back_url": "guests_list",
            "multipart": True,
        },
    )


@require_roles(ROLES_RECEPTION)
@login_required
def guest_id_view(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(Guest, pk=pk, property_profile=prop)
    if not obj.id_document:
        messages.error(request, "No ID document uploaded for this guest.")
        return redirect("guests_list")

    back_url = (request.GET.get("back") or "").strip()
    if not back_url.startswith("/"):
        back_url = reverse("guests_list")

    filename = os.path.basename(obj.id_document.name or "guest_id")
    guessed_type, _ = mimetypes.guess_type(filename)
    mime_type = guessed_type or "application/octet-stream"

    if request.GET.get("raw") != "1":
        base = reverse("guest_id_view", args=[obj.pk])
        return render(
            request,
            "core/guest_id_view.html",
            {
                "prop": prop,
                "guest": obj,
                "back_url": back_url,
                "file_name": filename,
                "mime_type": mime_type,
                "is_image": mime_type.startswith("image/"),
                "is_pdf": mime_type == "application/pdf",
                "file_url": f"{base}?raw=1",
                "download_url": f"{base}?raw=1&download=1",
            },
        )

    try:
        fh = obj.id_document.open("rb")
    except Exception:
        return HttpResponse("ID file not found.", status=404)

    disposition = "attachment" if request.GET.get("download") == "1" else "inline"
    response = FileResponse(
        fh,
        content_type=mime_type,
    )
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    return response


def _guest_export_rows(prop, q: str, id_q: str, phone_q: str):
    booking_type = _current_booking_type(prop)
    qs = Guest.objects.order_by("-created_at")
    if prop:
        other_type = BookingType.APARTMENT if booking_type == BookingType.HOTEL else BookingType.HOTEL
        qs = qs.filter(property_profile=prop)
        qs = qs.exclude(bookings__booking_type=other_type)
        qs = qs.filter(bookings__booking_type=booking_type)
    if q:
        qs = qs.filter(full_name__icontains=q)
    if id_q:
        qs = qs.filter(id_number__icontains=id_q)
    if phone_q:
        qs = qs.filter(phone__icontains=phone_q)

    guests = list(qs[:500])
    guest_ids = [g.id for g in guests]
    last_bookings = {}
    if guest_ids:
        bookings_qs = Booking.objects.filter(guest_id__in=guest_ids, booking_type=booking_type).order_by("guest_id", "-start_date")
        for b in bookings_qs:
            if b.guest_id not in last_bookings:
                last_bookings[b.guest_id] = b

    rows = []
    for g in guests:
        lb = last_bookings.get(g.id)
        rows.append(
            {
                "name": g.full_name,
                "id_number": g.id_number,
                "phone": g.phone,
                "address": g.address,
                "check_in": lb.start_date.isoformat() if lb else "",
                "check_out": lb.end_date.isoformat() if lb else "",
            }
        )
    return rows


@require_roles(ROLES_RECEPTION)
@login_required
def guests_report_print(request):
    prop = _get_active_property(request)
    q = (request.GET.get("q") or "").strip()
    id_q = (request.GET.get("id_number") or "").strip()
    phone_q = (request.GET.get("phone") or "").strip()
    back = (request.GET.get("back") or "").strip()
    is_desktop_qt = _is_desktop_qt_request(request)

    rows = _guest_export_rows(prop, q, id_q, phone_q)
    query = urlencode({"q": q, "id_number": id_q, "phone": phone_q})
    filters = {"q": q, "id_number": id_q, "phone": phone_q}
    is_ar = (request.GET.get("lang") or "").lower() == "ar"
    return render(
        request,
        "core/guests_report_print.html",
        {
            "prop": prop,
            "rows": rows,
            "query": query,
            "filters": filters,
            "is_ar": is_ar,
            "back": back,
            "is_desktop_qt": is_desktop_qt,
        },
    )


@require_roles(ROLES_RECEPTION)
@login_required
def guests_export_excel(request):
    prop = _get_active_property(request)
    q = (request.GET.get("q") or "").strip()
    id_q = (request.GET.get("id_number") or "").strip()
    phone_q = (request.GET.get("phone") or "").strip()

    rows = _guest_export_rows(prop, q, id_q, phone_q)

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    lang = (request.GET.get("lang") or "").lower()
    is_ar = lang == "ar"

    wb = Workbook()
    ws = wb.active
    ws.title = "Guests"

    title = "تقرير الضيوف" if is_ar else "Guests Report"
    property_label = "المنشأة" if is_ar else "Property"
    records_label = "إجمالي السجلات" if is_ar else "Total Records"
    generated_label = "تاريخ الإنشاء" if is_ar else "Generated At"

    headers = (
        ["الاسم", "رقم الهوية", "الهاتف", "العنوان", "تاريخ الوصول", "تاريخ المغادرة"]
        if is_ar
        else ["Name", "ID Number", "Phone", "Address", "Check-in", "Check-out"]
    )

    property_name = "-"
    if prop:
        property_name = (prop.name_ar or prop.name_en) if is_ar else (prop.name_en or prop.name_ar)
    from django.utils import timezone

    ws.merge_cells("A1:F1")
    ws["A1"] = title
    ws["A1"].font = Font(size=16, bold=True, color="0F2F63")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A2:C2")
    ws["A2"] = f"{property_label}: {property_name}"
    ws["A2"].font = Font(size=11, bold=True, color="1F2937")
    ws["A2"].alignment = Alignment(horizontal="left" if not is_ar else "right", vertical="center")

    ws.merge_cells("D2:F2")
    ws["D2"] = f"{records_label}: {len(rows)}"
    ws["D2"].font = Font(size=11, bold=True, color="1F2937")
    ws["D2"].alignment = Alignment(horizontal="right" if not is_ar else "left", vertical="center")

    ws.merge_cells("A3:F3")
    ws["A3"] = f"{generated_label}: {timezone.localtime().strftime('%Y-%m-%d %H:%M')}"
    ws["A3"].font = Font(size=9, color="6B7280")
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")

    ws.append([])
    ws.append(headers)

    header_row = 5
    thin = Side(style="thin", color="E5E7EB")
    for col in range(1, 7):
        cell = ws.cell(row=header_row, column=col)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(fill_type="solid", fgColor="0F2F63")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)

    data_alignment = Alignment(horizontal="right" if is_ar else "left", vertical="top", wrap_text=True)
    data_start = header_row + 1
    for idx, r in enumerate(rows, start=data_start):
        ws.cell(row=idx, column=1, value=r["name"] or "-")
        ws.cell(row=idx, column=2, value=r["id_number"] or "-")
        ws.cell(row=idx, column=3, value=r["phone"] or "-")
        ws.cell(row=idx, column=4, value=r["address"] or "-")
        ws.cell(row=idx, column=5, value=r["check_in"] or "-")
        ws.cell(row=idx, column=6, value=r["check_out"] or "-")

        for col in range(1, 7):
            cell = ws.cell(row=idx, column=col)
            cell.alignment = data_alignment
            cell.border = Border(top=thin, left=thin, right=thin, bottom=thin)
            if idx % 2 == 0:
                cell.fill = PatternFill(fill_type="solid", fgColor="F8FAFC")

    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 36
    ws.column_dimensions["E"].width = 16
    ws.column_dimensions["F"].width = 16
    ws.freeze_panes = "A6"

    resp = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = "attachment; filename=guests_report_modern.xlsx"
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    wb.save(resp)
    return resp


@require_roles(ROLES_RECEPTION)
@login_required
def guests_export_pdf(request):
    prop = _get_active_property(request)
    q = (request.GET.get("q") or "").strip()
    id_q = (request.GET.get("id_number") or "").strip()
    phone_q = (request.GET.get("phone") or "").strip()

    rows = _guest_export_rows(prop, q, id_q, phone_q)
    is_ar = (request.GET.get("lang") or "").lower() == "ar"

    resp = HttpResponse(content_type="application/pdf")
    resp["Content-Disposition"] = "attachment; filename=guests_report_modern.pdf"
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"

    title = "تقرير الضيوف" if is_ar else "Guests Report"
    subtitle = (
        f"إجمالي السجلات: {len(rows)}<br/>الاسم: {q or '-'} | الهوية: {id_q or '-'} | الهاتف: {phone_q or '-'}"
        if is_ar
        else f"Total Records: {len(rows)}<br/>Name: {q or '-'} | ID: {id_q or '-'} | Phone: {phone_q or '-'}"
    )
    headers = (
        ["الاسم", "رقم الهوية", "الهاتف", "العنوان", "تاريخ الوصول", "تاريخ المغادرة"]
        if is_ar
        else ["Name", "ID Number", "Phone", "Address", "Check-in", "Check-out"]
    )
    data_rows = [
        [
            str(r.get("name") or "-"),
            str(r.get("id_number") or "-"),
            str(r.get("phone") or "-"),
            str(r.get("address") or "-"),
            str(r.get("check_in") or "-"),
            str(r.get("check_out") or "-"),
        ]
        for r in rows
    ]

    _build_modern_pdf_report(
        resp,
        prop=prop,
        title=title,
        subtitle=subtitle,
        headers=headers,
        rows=data_rows,
        col_width_mm=[40, 28, 28, 50, 22, 22],
        is_ar=is_ar,
    )
    return resp


def _get_reportlab_fonts(is_ar: bool):
    default_font = "Helvetica"
    bold_font = "Helvetica-Bold"
    if not is_ar:
        return default_font, bold_font
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        def _register(alias: str, path: str) -> str | None:
            if not path or not os.path.exists(path):
                return None
            try:
                if alias not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(alias, path))
                return alias
            except Exception:
                return None

        win_fonts = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        # Prefer Cairo first for Arabic branding, then stable Windows fallbacks.
        bundled_fonts = os.path.join(settings.BASE_DIR, "web", "assets", "fonts")
        regular_candidates = [
            os.path.join(bundled_fonts, "Cairo-Regular.ttf"),
            os.path.join(bundled_fonts, "Cairo-Variable.ttf"),
            os.path.join(settings.BASE_DIR, "owner_admin_app", "assets", "fonts", "Cairo-Regular.ttf"),
            os.path.join(settings.BASE_DIR, "owner_admin_app", "assets", "fonts", "Cairo-Variable.ttf"),
            os.path.join(bundled_fonts, "tahoma.ttf"),
            r"C:\Windows\Fonts\tahoma.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            os.path.join(win_fonts, "tahoma.ttf"),
            os.path.join(win_fonts, "arial.ttf"),
            os.path.join(win_fonts, "segoeui.ttf"),
        ]
        bold_candidates = [
            os.path.join(bundled_fonts, "Cairo-Bold.ttf"),
            os.path.join(bundled_fonts, "Cairo-Variable.ttf"),
            os.path.join(settings.BASE_DIR, "owner_admin_app", "assets", "fonts", "Cairo-Bold.ttf"),
            os.path.join(settings.BASE_DIR, "owner_admin_app", "assets", "fonts", "Cairo-Variable.ttf"),
            os.path.join(bundled_fonts, "tahomabd.ttf"),
            r"C:\Windows\Fonts\tahomabd.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            os.path.join(win_fonts, "tahomabd.ttf"),
            os.path.join(win_fonts, "arialbd.ttf"),
            os.path.join(win_fonts, "segoeuib.ttf"),
        ]

        picked_regular = None
        for path in regular_candidates:
            picked_regular = _register("SLXArabicRegular", path)
            if picked_regular:
                break
        picked_bold = None
        for path in bold_candidates:
            picked_bold = _register("SLXArabicBold", path)
            if picked_bold:
                break
        if picked_regular:
            return picked_regular, (picked_bold or picked_regular)
    except Exception:
        pass
    return default_font, bold_font


def _prepare_pdf_text(value, is_ar: bool = False) -> str:
    text = str(value or "")
    if not is_ar:
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def _build_modern_pdf_report(
    response: HttpResponse,
    *,
    prop,
    title: str,
    subtitle: str,
    headers: list[str],
    rows: list[list[str]],
    col_width_mm: list[float],
    is_ar: bool = False,
):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    default_font, bold_font = _get_reportlab_fonts(is_ar)
    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()
    text_style = ParagraphStyle(
        "ModernText",
        parent=styles["Normal"],
        fontName=default_font,
        fontSize=9,
        leading=12,
        alignment=2 if is_ar else 0,
        textColor=colors.HexColor("#0B1F3F"),
    )
    title_style = ParagraphStyle(
        "ModernTitle",
        parent=styles["Heading1"],
        fontName=bold_font,
        fontSize=16,
        leading=20,
        alignment=2 if is_ar else 0,
        textColor=colors.HexColor("#0F2F63"),
    )
    subtitle_style = ParagraphStyle(
        "ModernSubtitle",
        parent=styles["Normal"],
        fontName=default_font,
        fontSize=9,
        leading=12,
        alignment=2 if is_ar else 0,
        textColor=colors.HexColor("#64748B"),
    )

    elements = []
    property_name = "-"
    property_address = "-"
    if prop:
        property_name = (prop.name_ar or prop.name_en) if is_ar else (prop.name_en or prop.name_ar)
        property_address = (prop.address_ar or prop.address_en) if is_ar else (prop.address_en or prop.address_ar)
    property_name = _prepare_pdf_text(property_name, is_ar)
    property_address = _prepare_pdf_text(property_address, is_ar)
    display_title = _prepare_pdf_text(title, is_ar)
    if is_ar and "<br/>" in subtitle:
        display_subtitle = "<br/>".join(_prepare_pdf_text(part, True) for part in subtitle.split("<br/>"))
    else:
        display_subtitle = _prepare_pdf_text(subtitle, is_ar)

    head_cells = []
    if prop and getattr(prop, "logo", None) and hasattr(prop.logo, "path"):
        try:
            head_cells.append(Image(prop.logo.path, width=15 * mm, height=15 * mm))
        except Exception:
            head_cells.append(Paragraph("", text_style))
    else:
        head_cells.append(Paragraph("", text_style))

    # Align property block to match page direction.
    property_block = Paragraph(
        f"{property_name}<br/>{property_address}",
        ParagraphStyle(
            "PropertyBlock",
            parent=text_style,
            alignment=2 if is_ar else 0,
        ),
    )
    head_cells.append(property_block)

    title_cell = Table(
        [
            [
                Paragraph(
                    display_title,
                    ParagraphStyle("TitleCellHead", parent=title_style, alignment=2 if is_ar else 2),
                )
            ],
            [
                Paragraph(
                    display_subtitle,
                    ParagraphStyle("TitleCellSub", parent=subtitle_style, alignment=2 if is_ar else 2),
                )
            ],
        ],
        colWidths=[74 * mm],
    )
    title_cell.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    head_cells.append(title_cell)

    if is_ar:
        # Mirror layout for Arabic: report title block on the left,
        # property block on the right (with logo on the far right).
        header = Table([[title_cell, property_block, head_cells[0]]], colWidths=[74 * mm, 88 * mm, 18 * mm])
        header.hAlign = "LEFT"
    else:
        header = Table([head_cells], colWidths=[18 * mm, 88 * mm, 74 * mm])
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor("#E5E7EB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(header)
    elements.append(Spacer(1, 4 * mm))

    header_row = [Paragraph(_prepare_pdf_text(h, is_ar), text_style) for h in headers]
    table_data = [list(reversed(header_row)) if is_ar else header_row]
    if rows:
        for row in rows:
            row_cells = [Paragraph(_prepare_pdf_text(v or "-", is_ar), text_style) for v in row]
            table_data.append(list(reversed(row_cells)) if is_ar else row_cells)
    else:
        empty = _prepare_pdf_text("لا توجد بيانات متاحة." if is_ar else "No data available.", is_ar)
        table_data.append([Paragraph(empty, text_style)] + [""] * (len(headers) - 1))

    tbl = Table(table_data, repeatRows=1, colWidths=[w * mm for w in col_width_mm])
    styles_list = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2F63")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            styles_list.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F8FAFC")))
    if not rows:
        styles_list.extend([("SPAN", (0, 1), (-1, 1)), ("ALIGN", (0, 1), (-1, 1), "CENTER")])
    tbl.setStyle(TableStyle(styles_list))
    elements.append(tbl)
    doc.build(elements)


def _build_invoice_pdf(response: HttpResponse, *, invoice: Invoice, prop, is_ar: bool = False):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    default_font, bold_font = _get_reportlab_fonts(is_ar)
    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "InvoiceBody",
        parent=styles["Normal"],
        fontName=default_font,
        fontSize=10.5,
        leading=14,
        alignment=2 if is_ar else 0,
        textColor=colors.HexColor("#0B1F3F"),
    )
    body_muted = ParagraphStyle(
        "InvoiceMuted",
        parent=body,
        textColor=colors.HexColor("#64748B"),
        fontSize=9,
        leading=12,
    )
    title_style = ParagraphStyle(
        "InvoiceTitle",
        parent=styles["Heading1"],
        fontName=bold_font,
        fontSize=28,
        leading=32,
        alignment=2 if is_ar else 2,
        textColor=colors.HexColor("#0F2F63"),
    )
    section_title = ParagraphStyle(
        "InvoiceSectionTitle",
        parent=body,
        fontName=bold_font,
        fontSize=10,
        textColor=colors.HexColor("#475569"),
    )

    elements = []

    property_name = (prop.name_ar or prop.name_en) if is_ar else (prop.name_en or prop.name_ar)
    property_address = (prop.address_ar or prop.address_en) if is_ar else (prop.address_en or prop.address_ar)
    property_name = _prepare_pdf_text(property_name or "StayLux", is_ar)
    property_address = _prepare_pdf_text(property_address or "-", is_ar)

    status_map_ar = {
        "draft": "مسودة",
        "issued": "صادرة",
        "paid": "مدفوعة",
        "partially_paid": "مدفوعة جزئياً",
        "overdue": "متأخرة",
        "cancelled": "ملغاة",
    }
    status_label = status_map_ar.get((invoice.status or "").lower(), invoice.status or "-") if is_ar else (invoice.status or "-")
    status_label = _prepare_pdf_text(status_label, is_ar)
    title_text = _prepare_pdf_text("فاتورة" if is_ar else "Invoice", is_ar)

    left_block_items = []
    if prop and getattr(prop, "logo", None) and hasattr(prop.logo, "path"):
        try:
            left_block_items.append(Image(prop.logo.path, width=14 * mm, height=14 * mm))
        except Exception:
            left_block_items.append(Paragraph("", body))
    else:
        left_block_items.append(Paragraph("", body))
    left_block_items.append(
        Paragraph(
            f"<b><font size='20'>{property_name}</font></b><br/><font size='11'>{property_address}</font>",
            ParagraphStyle(
                "InvoicePropertyBlock",
                parent=body,
                alignment=0,
            ),
        )
    )
    left_block = Table([left_block_items], colWidths=[18 * mm, 106 * mm])
    left_block.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("BOX", (0, 0), (0, 0), 0.6, colors.HexColor("#E2E8F0")),
            ]
        )
    )

    invoice_meta = (
        f"{_prepare_pdf_text('رقم الفاتورة' if is_ar else 'Invoice #', is_ar)}: {invoice.invoice_no or invoice.id}<br/>"
        f"{_prepare_pdf_text('تاريخ الإنشاء' if is_ar else 'Created', is_ar)}: {invoice.created_at.strftime('%Y-%m-%d %H:%M')}<br/>"
        f"{_prepare_pdf_text('تاريخ الإصدار' if is_ar else 'Issue', is_ar)}: {invoice.issue_date or '-'}<br/>"
        f"{_prepare_pdf_text('تاريخ الاستحقاق' if is_ar else 'Due', is_ar)}: {invoice.due_date or '-'}"
    )
    status_badge = Table([[Paragraph(status_label, ParagraphStyle("InvoiceStatusBadge", parent=body_muted, alignment=1))]], colWidths=[20 * mm])
    status_badge.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )

    right_block = Table(
        [
            [Paragraph(title_text, title_style)],
            [status_badge],
            [Paragraph(invoice_meta, body_muted)],
            [Paragraph("", body_muted)],
        ],
        colWidths=[66 * mm],
    )
    right_block.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    header = Table(
        [[left_block, right_block]],
        colWidths=[124 * mm, 66 * mm],
        rowHeights=[38 * mm],
        hAlign="LEFT",
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor("#E5E7EB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    elements.append(header)
    elements.append(Spacer(1, 6 * mm))

    bill_to_title = _prepare_pdf_text("بيانات العميل" if is_ar else "Bill To", is_ar)
    summary_title = _prepare_pdf_text("الملخص" if is_ar else "Summary", is_ar)
    phone_label = _prepare_pdf_text("الهاتف" if is_ar else "Phone", is_ar)
    whatsapp_label = _prepare_pdf_text("واتساب" if is_ar else "WhatsApp", is_ar)
    email_label = _prepare_pdf_text("البريد الإلكتروني" if is_ar else "Email", is_ar)
    total_label = _prepare_pdf_text("الإجمالي" if is_ar else "Total", is_ar)
    paid_label = _prepare_pdf_text("المدفوع" if is_ar else "Paid", is_ar)
    balance_label = _prepare_pdf_text("المتبقي" if is_ar else "Balance", is_ar)

    guest_info = (
        [
            f"<b>{_prepare_pdf_text(invoice.guest.full_name or '-', is_ar)}</b>",
            f"{_prepare_pdf_text(invoice.guest.phone or '-', is_ar)} :{phone_label}",
            f"{_prepare_pdf_text(invoice.guest.whatsapp or '-', is_ar)} :{whatsapp_label}",
            f"{_prepare_pdf_text(invoice.guest.email or '-', is_ar)} :{email_label}",
        ]
        if is_ar
        else [
            f"<b>{_prepare_pdf_text(invoice.guest.full_name or '-', is_ar)}</b>",
            f"{phone_label}: {_prepare_pdf_text(invoice.guest.phone or '-', is_ar)}",
            f"{whatsapp_label}: {_prepare_pdf_text(invoice.guest.whatsapp or '-', is_ar)}",
            f"{email_label}: {_prepare_pdf_text(invoice.guest.email or '-', is_ar)}",
        ]
    )
    summary_info = (
        [
            f"{invoice.currency} {invoice.total:.3f} :{total_label}",
            f"{invoice.currency} {invoice.amount_paid:.3f} :{paid_label}",
            f"{invoice.currency} {invoice.balance_due:.3f} :{balance_label}",
        ]
        if is_ar
        else [
            f"{total_label}: {invoice.total:.3f} {invoice.currency}",
            f"{paid_label}: {invoice.amount_paid:.3f} {invoice.currency}",
            f"{balance_label}: {invoice.balance_due:.3f} {invoice.currency}",
        ]
    )
    guest_par = Paragraph(
        "<br/>".join(guest_info),
        ParagraphStyle("InvoiceGuestPar", parent=body, alignment=2 if is_ar else 0),
    )
    summary_par = Paragraph(
        "<br/>".join(summary_info),
        ParagraphStyle("InvoiceSummaryPar", parent=body, alignment=0 if is_ar else 0),
    )

    top_info = Table(
        [
            [Paragraph(bill_to_title, section_title), Paragraph(summary_title, section_title)],
            [guest_par, summary_par],
        ],
        colWidths=[95 * mm, 95 * mm],
        hAlign="LEFT",
    )
    if is_ar:
        summary_title_style_ar = ParagraphStyle("InvoiceSummaryTitleAr", parent=section_title, alignment=0)
        guest_title_style_ar = ParagraphStyle("InvoiceGuestTitleAr", parent=section_title, alignment=2)
        top_info = Table(
            [
                [Paragraph(summary_title, summary_title_style_ar), Paragraph(bill_to_title, guest_title_style_ar)],
                [summary_par, guest_par],
            ],
            colWidths=[95 * mm, 95 * mm],
            hAlign="LEFT",
        )
    top_info.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E5E7EB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(top_info)
    elements.append(Spacer(1, 4 * mm))

    headers = (
        ["الوصف", "الكمية", "سعر الوحدة", "الخصم", "الضريبة", "إجمالي البند"]
        if is_ar
        else ["Description", "Qty", "Unit Price", "Discount", "Tax", "Line Total"]
    )
    line_rows = [
        [
            str(line.description or "-"),
            str(line.quantity or "0"),
            str(line.unit_price or "0"),
            str(line.discount_amount or "0"),
            str(line.tax_amount or "0"),
            str(line.line_total or "0"),
        ]
        for line in invoice.lines.all()
    ]
    table_data = [[Paragraph(_prepare_pdf_text(h, is_ar), body) for h in (reversed(headers) if is_ar else headers)]]
    for r in line_rows:
        vals = list(reversed(r)) if is_ar else r
        table_data.append([Paragraph(_prepare_pdf_text(v, is_ar), body) for v in vals])
    if not line_rows:
        msg = _prepare_pdf_text("لا توجد بنود." if is_ar else "No lines yet.", is_ar)
        table_data.append([Paragraph(msg, body)] + [""] * (len(headers) - 1))

    lines_tbl = Table(
        table_data,
        repeatRows=1,
        colWidths=[24 * mm, 20 * mm, 20 * mm, 24 * mm, 16 * mm, 86 * mm] if is_ar else [86 * mm, 16 * mm, 24 * mm, 20 * mm, 20 * mm, 24 * mm],
        hAlign="LEFT",
    )
    line_styles = [
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.HexColor("#CBD5E1")),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT" if is_ar else "LEFT"),
    ]
    if not line_rows:
        line_styles.extend([("SPAN", (0, 1), (-1, 1)), ("ALIGN", (0, 1), (-1, 1), "CENTER")])
    lines_tbl.setStyle(TableStyle(line_styles))
    elements.append(lines_tbl)
    elements.append(Spacer(1, 5 * mm))

    totals_labels = (
        ["الإجمالي قبل الخصم", "الخصم", "الضريبة", "الإجمالي", "المدفوع", "الرصيد المستحق"]
        if is_ar
        else ["Subtotal", "Discount", "Tax", "Total", "Paid", "Balance Due"]
    )
    totals_vals = [
        f"{invoice.currency} {invoice.subtotal:.3f}" if is_ar else f"{invoice.subtotal:.3f} {invoice.currency}",
        f"{invoice.currency} {invoice.discount_total:.3f}" if is_ar else f"{invoice.discount_total:.3f} {invoice.currency}",
        f"{invoice.currency} {invoice.tax_total:.3f}" if is_ar else f"{invoice.tax_total:.3f} {invoice.currency}",
        f"{invoice.currency} {invoice.total:.3f}" if is_ar else f"{invoice.total:.3f} {invoice.currency}",
        f"{invoice.currency} {invoice.amount_paid:.3f}" if is_ar else f"{invoice.amount_paid:.3f} {invoice.currency}",
        f"{invoice.currency} {invoice.balance_due:.3f}" if is_ar else f"{invoice.balance_due:.3f} {invoice.currency}",
    ]
    totals_data = []
    for label, value in zip(totals_labels, totals_vals):
        if is_ar:
            totals_data.append([Paragraph(_prepare_pdf_text(value, True), body), Paragraph(_prepare_pdf_text(label, True), section_title)])
        else:
            totals_data.append([Paragraph(_prepare_pdf_text(label, False), section_title), Paragraph(_prepare_pdf_text(value, False), body)])

    totals_tbl = Table(totals_data, colWidths=[45 * mm, 45 * mm])
    totals_tbl.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT" if is_ar else "LEFT"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#E5E7EB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    totals_wrap = Table([[totals_tbl]], colWidths=[95 * mm], hAlign="LEFT" if is_ar else "RIGHT")
    elements.append(totals_wrap)

    phone_label_footer = _prepare_pdf_text("الهاتف" if is_ar else "Phone", is_ar)
    address_label_footer = _prepare_pdf_text("العنوان" if is_ar else "Address", is_ar)
    phone_text = _prepare_pdf_text(getattr(prop, "phone", "") or "-", is_ar)
    address_text = _prepare_pdf_text((prop.address_ar or prop.address_en) if is_ar else (prop.address_en or prop.address_ar) or "-", is_ar)
    footer = Table(
        [[
            Paragraph(f"{address_label_footer}: {address_text}", body_muted),
            Paragraph(f"{phone_label_footer}: {phone_text}", body_muted),
        ]] if is_ar else [[
            Paragraph(f"{phone_label_footer}: {phone_text}", body_muted),
            Paragraph(f"{address_label_footer}: {address_text}", body_muted),
        ]],
        colWidths=[95 * mm, 95 * mm],
        hAlign="LEFT",
    )
    footer.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, -1), 1, colors.HexColor("#E5E7EB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT" if is_ar else "LEFT"),
            ]
        )
    )
    elements.append(Spacer(1, 4 * mm))
    elements.append(footer)

    doc.build(elements)


def _build_agreement_pdf(
    response: HttpResponse,
    *,
    group: BookingGroup,
    guest,
    units: list,
    currency: str,
    total: Decimal,
    advance: Decimal,
    balance: Decimal,
    prop,
    is_ar: bool = False,
):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    default_font, bold_font = _get_reportlab_fonts(is_ar)
    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "AgreementBody",
        parent=styles["Normal"],
        fontName=default_font,
        fontSize=11,
        leading=15,
        alignment=2 if is_ar else 0,
        textColor=colors.HexColor("#0B1F3F"),
    )
    muted = ParagraphStyle(
        "AgreementMuted",
        parent=body,
        fontSize=9,
        textColor=colors.HexColor("#64748B"),
    )
    title_style = ParagraphStyle(
        "AgreementTitle",
        parent=styles["Heading1"],
        fontName=bold_font,
        fontSize=28,
        leading=32,
        alignment=2 if is_ar else 2,
        textColor=colors.HexColor("#0F2F63"),
    )
    section_title = ParagraphStyle(
        "AgreementSectionTitle",
        parent=body,
        fontName=bold_font,
        fontSize=10,
        textColor=colors.HexColor("#475569"),
    )

    elements = []
    property_name = (prop.name_ar or prop.name_en) if is_ar else (prop.name_en or prop.name_ar)
    property_address = (prop.address_ar or prop.address_en) if is_ar else (prop.address_en or prop.address_ar)
    property_name = _prepare_pdf_text(property_name or "StayLux", is_ar)
    property_address = _prepare_pdf_text(property_address or "-", is_ar)
    title_text = _prepare_pdf_text("اتفاقية حجز" if is_ar else "Booking Agreement", is_ar)

    left_block_items = []
    if prop and getattr(prop, "logo", None) and hasattr(prop.logo, "path"):
        try:
            left_block_items.append(Image(prop.logo.path, width=14 * mm, height=14 * mm))
        except Exception:
            left_block_items.append(Paragraph("", body))
    else:
        left_block_items.append(Paragraph("", body))
    left_block_items.append(
        Paragraph(
            f"<b><font size='20'>{property_name}</font></b><br/><font size='10'>{property_address}</font>",
            body,
        )
    )
    left_block = Table([left_block_items], colWidths=[18 * mm, 106 * mm])
    left_block.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("BOX", (0, 0), (0, 0), 0.6, colors.HexColor("#E2E8F0")),
            ]
        )
    )

    meta_block = (
        f"{_prepare_pdf_text('رقم الاتفاقية' if is_ar else 'Agreement No', is_ar)}: {group.id}<br/>"
        f"{_prepare_pdf_text('التاريخ' if is_ar else 'Created', is_ar)}: {group.created_at.strftime('%Y-%m-%d')}"
    )
    right_block = Table(
        [
            [Paragraph(title_text, title_style)],
            [Paragraph(meta_block, muted)],
        ],
        colWidths=[66 * mm],
    )
    right_block.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    header = Table(
        [[left_block, right_block]],
        colWidths=[124 * mm, 66 * mm],
        rowHeights=[38 * mm],
        hAlign="LEFT",
    )
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 1, colors.HexColor("#E5E7EB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(header)
    elements.append(Spacer(1, 6 * mm))

    units_text = ", ".join([u.code for u in units]) if units else "-"
    guest_title = _prepare_pdf_text("الضيف" if is_ar else "Guest", is_ar)
    stay_title = _prepare_pdf_text("الإقامة" if is_ar else "Stay", is_ar)
    guest_info = (
        f"<b>{_prepare_pdf_text(guest.full_name or '-', is_ar)}</b><br/>"
        f"{_prepare_pdf_text('الهاتف' if is_ar else 'Phone', is_ar)}: {_prepare_pdf_text(guest.phone or '-', is_ar)}"
    )
    stay_info = (
        f"{_prepare_pdf_text('الدخول' if is_ar else 'Check-in', is_ar)}: {_prepare_pdf_text(group.start_date, is_ar)}<br/>"
        f"{_prepare_pdf_text('الخروج' if is_ar else 'Check-out', is_ar)}: {_prepare_pdf_text(group.end_date, is_ar)}<br/>"
        f"{_prepare_pdf_text('الوحدات' if is_ar else 'Units', is_ar)}: {_prepare_pdf_text(units_text, is_ar)}"
    )
    guest_card = Table(
        [[Paragraph(guest_title, section_title)], [Paragraph(guest_info, body)]],
        colWidths=[93 * mm],
        hAlign="LEFT",
    )
    guest_card.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#E2E8F0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    stay_card = Table(
        [[Paragraph(stay_title, section_title)], [Paragraph(stay_info, body)]],
        colWidths=[93 * mm],
        hAlign="LEFT",
    )
    stay_card.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#E2E8F0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    stay_guest = Table(
        [[stay_card, guest_card]] if is_ar else [[guest_card, stay_card]],
        colWidths=[95 * mm, 95 * mm],
        hAlign="LEFT",
    )
    stay_guest.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(stay_guest)
    elements.append(Spacer(1, 4 * mm))

    pricing_title = _prepare_pdf_text("الأسعار" if is_ar else "Pricing", is_ar)
    pricing_rows = [
        (
            _prepare_pdf_text("الإجمالي" if is_ar else "Total", is_ar),
            f"{currency} {total:.3f}" if is_ar else f"{total:.3f} {currency}",
        ),
        (
            _prepare_pdf_text("الدفعة المقدمة" if is_ar else "Advance", is_ar),
            f"{currency} {advance:.3f}" if is_ar else f"{advance:.3f} {currency}",
        ),
        (
            _prepare_pdf_text("المتبقي" if is_ar else "Balance", is_ar),
            f"{currency} {balance:.3f}" if is_ar else f"{balance:.3f} {currency}",
        ),
    ]
    price_data = [[Paragraph(pricing_title, section_title), Paragraph("", body)]]
    for label, value in pricing_rows:
        price_data.append(
            [Paragraph(_prepare_pdf_text(value, is_ar), body), Paragraph(label, body)]
            if is_ar
            else [Paragraph(label, body), Paragraph(value, body)]
        )
    pricing_tbl = Table(price_data, colWidths=[95 * mm, 95 * mm], hAlign="LEFT")
    pricing_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#E2E8F0")),
                ("SPAN", (0, 0), (-1, 0)),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT" if is_ar else "LEFT"),
            ]
        )
    )
    elements.append(pricing_tbl)
    elements.append(Spacer(1, 4 * mm))

    terms_title = _prepare_pdf_text("الشروط" if is_ar else "Terms", is_ar)
    terms_lines = [
        _prepare_pdf_text(
            "1. يلتزم الضيف بتعليمات المنشأة والسياسات."
            if is_ar
            else "1. Guest agrees to comply with property rules and policies.",
            is_ar,
        ),
        _prepare_pdf_text(
            "2. قد يتم احتساب رسوم إضافية عن الأضرار أو الفقد."
            if is_ar
            else "2. Damage or loss may incur additional charges.",
            is_ar,
        ),
        _prepare_pdf_text(
            "3. أوقات الدخول والخروج قابلة للتعديل حسب التوفر."
            if is_ar
            else "3. Check-in/out times and extensions are subject to availability.",
            is_ar,
        ),
    ]
    terms_tbl = Table(
        [[Paragraph(terms_title, section_title)], [Paragraph("<br/>".join(terms_lines), body)]],
        colWidths=[190 * mm],
        hAlign="LEFT",
    )
    terms_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#E2E8F0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(terms_tbl)
    elements.append(Spacer(1, 4 * mm))

    sig_title = _prepare_pdf_text("التوقيع" if is_ar else "Signatures", is_ar)
    left_sig = _prepare_pdf_text("توقيع المشغل" if is_ar else "Operator Signature", is_ar)
    right_sig = _prepare_pdf_text("توقيع الضيف" if is_ar else "Guest Signature", is_ar)
    sig_tbl = Table(
        [
            [Paragraph(sig_title, section_title), Paragraph("", body)],
            [Paragraph(right_sig, body), Paragraph(left_sig, body)] if is_ar else [Paragraph(left_sig, body), Paragraph(right_sig, body)],
            [Paragraph("________________________", body), Paragraph("________________________", body)],
        ],
        colWidths=[95 * mm, 95 * mm],
        hAlign="LEFT",
    )
    sig_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#E2E8F0")),
                ("SPAN", (0, 0), (-1, 0)),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT" if is_ar else "LEFT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(sig_tbl)

    phone_label_footer = _prepare_pdf_text("الهاتف" if is_ar else "Phone", is_ar)
    address_label_footer = _prepare_pdf_text("العنوان" if is_ar else "Address", is_ar)
    phone_text = _prepare_pdf_text(getattr(prop, "phone", "") or "-", is_ar)
    address_text = _prepare_pdf_text((prop.address_ar or prop.address_en) if is_ar else (prop.address_en or prop.address_ar) or "-", is_ar)
    footer = Table(
        [[
            Paragraph(f"{address_label_footer}: {address_text}", muted),
            Paragraph(f"{phone_label_footer}: {phone_text}", muted),
        ]] if is_ar else [[
            Paragraph(f"{phone_label_footer}: {phone_text}", muted),
            Paragraph(f"{address_label_footer}: {address_text}", muted),
        ]],
        colWidths=[95 * mm, 95 * mm],
        hAlign="LEFT",
    )
    footer.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 0), (-1, -1), 1, colors.HexColor("#E5E7EB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT" if is_ar else "LEFT"),
            ]
        )
    )
    elements.append(Spacer(1, 4 * mm))
    elements.append(footer)

    doc.build(elements)


def _build_modern_excel_report(
    *,
    title: str,
    sheet_title: str,
    headers: list[str],
    rows: list[list],
    filename: str,
    prop=None,
    is_ar: bool = False,
):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    ws.cell(row=1, column=1, value=title)
    ws.cell(row=1, column=1).font = Font(size=16, bold=True, color="0F2F63")
    ws.cell(row=1, column=1).alignment = Alignment(horizontal="center")

    property_name = "-"
    if prop:
        property_name = (prop.name_ar or prop.name_en) if is_ar else (prop.name_en or prop.name_ar)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(headers))
    ws.cell(row=2, column=1, value=property_name)
    ws.cell(row=2, column=1).font = Font(size=10, bold=True, color="334155")
    ws.cell(row=2, column=1).alignment = Alignment(horizontal="center")

    ws.append([])
    ws.append(headers)
    head_row = 4
    thin = Side(style="thin", color="E5E7EB")
    for col in range(1, len(headers) + 1):
        c = ws.cell(row=head_row, column=col)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill(fill_type="solid", fgColor="0F2F63")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = Border(left=thin, right=thin, top=thin, bottom=thin)

    align = Alignment(horizontal="right" if is_ar else "left", vertical="top", wrap_text=True)
    start = head_row + 1
    for i, row in enumerate(rows, start=start):
        for j, val in enumerate(row, start=1):
            c = ws.cell(row=i, column=j, value=val if val not in (None, "") else "-")
            c.alignment = align
            c.border = Border(left=thin, right=thin, top=thin, bottom=thin)
            if i % 2 == 0:
                c.fill = PatternFill(fill_type="solid", fgColor="F8FAFC")

    for idx in range(1, len(headers) + 1):
        ws.column_dimensions[chr(64 + idx)].width = 18
    ws.freeze_panes = f"A{start}"

    resp = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = f"attachment; filename={filename}"
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    wb.save(resp)
    return resp


@require_roles(ROLES_RECEPTION)
@login_required
def guest_create(request):
    prop = _get_active_property(request)
    form = GuestForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.property_profile = prop
        if prop:
            obj.business_type = prop.business_type
        obj.save()
        messages.success(request, _("Guest created."))
        return redirect("guests_list")

    return render(
        request,
        "core/form_page.html",
        {
            "prop": prop,
            "title": _("Add Guest"),
            "form": form,
            "back_url": "guests_list",
            "multipart": True,
        },
    )


@require_roles(ROLES_RECEPTION)
@login_required
def guest_edit(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(Guest, pk=pk, property_profile=prop)
    form = GuestForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Guest updated."))
        return redirect("guests_list")

    return render(
        request,
        "core/form_page.html",
        {
            "prop": prop,
            "title": _("Edit Guest #%(id)s") % {"id": obj.id},
            "form": form,
            "back_url": "guests_list",
            "multipart": True,
        },
    )


@require_roles(ROLES_RECEPTION)
@login_required
def guest_delete(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(Guest, pk=pk, property_profile=prop)
    if request.method == "POST":
        try:
            obj.delete()
            messages.success(request, _("Guest deleted."))
        except ProtectedError:
            if obj.is_active:
                obj.is_active = False
                obj.save(update_fields=["is_active", "updated_at"])
            messages.warning(request, _("Guest has bookings and cannot be deleted. Deactivated instead."))
        return redirect("guests_list")

    return render(
        request,
        "core/confirm_delete.html",
        {
            "prop": prop,
            "title": "Delete Guest",
            "object_label": obj.full_name,
            "back_url": "guests_list",
        },
    )



# =========================================================
# MAINTENANCE (CRUD)
# =========================================================
@require_roles(ROLES_MAINTENANCE_VIEW)
@login_required
def maintenance_list(request):
    prop = _get_active_property(request)
    qs = MaintenanceRequest.objects.select_related("unit").order_by("-created_at")
    if prop:
        qs = qs.filter(property_profile=prop, unit__unit_type__business_type=prop.business_type)
    status_q = (request.GET.get("status") or "").strip()
    unit_q = (request.GET.get("unit") or "").strip()
    assigned_q = (request.GET.get("assigned") or "").strip()
    if status_q:
        qs = qs.filter(status=status_q)
    if unit_q:
        qs = qs.filter(unit__code__icontains=unit_q)
    if assigned_q:
        qs = qs.filter(assigned_to__user__username__icontains=assigned_q)
    return render(request, "core/maintenance_list.html", {"prop": prop, "tickets": qs[:500], "filters": {"status": status_q, "unit": unit_q, "assigned": assigned_q}})


@require_roles(ROLES_MAINTENANCE)
@login_required
def maintenance_create(request):
    prop = _get_active_property(request)
    initial = {}
    if request.GET.get("unit"):
        initial["unit"] = request.GET.get("unit")
    action = (request.POST.get("action") or "").strip() or "draft"
    form = MaintenanceDraftForm(
        request.POST or None,
        request.FILES or None,
        property_obj=prop,
        initial=initial,
        action=action,
    )
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.property_profile = prop
        if action == "draft":
            obj.status = MaintenanceStatus.OPEN
        elif action == "start":
            obj.status = MaintenanceStatus.IN_PROGRESS
        obj.save()

        try:
            from inventory.models import UnitStatus
            obj.unit.status = UnitStatus.MAINTENANCE
            obj.unit.save(update_fields=["status", "updated_at"])
        except Exception:
            pass

        messages.success(request, _("Maintenance ticket created."))
        return redirect("maintenance_list")
    form_actions = [
        {"value": "draft", "label": _("Save Draft"), "class": "btn btn-sm"},
        {"value": "start", "label": _("Start Work"), "class": "btn btn-sm btn-primary"},
    ]
    is_ar = str(getattr(request, "LANGUAGE_CODE", "")).lower().startswith("ar")
    return render(
        request,
        "core/form_page.html",
        {
            "prop": prop,
            "title": "الخطوة 1 للصيانة - مسودة" if is_ar else _("Maintenance Step 1 - Draft"),
            "form": form,
            "back_url": "maintenance_list",
            "multipart": True,
            "form_actions": form_actions,
        },
    )


@require_roles(ROLES_MAINTENANCE)
@login_required
def maintenance_edit(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(MaintenanceRequest, pk=pk, property_profile=prop)
    action = (request.POST.get("action") or "").strip()
    form = MaintenanceDraftForm(
        request.POST or None,
        request.FILES or None,
        instance=obj,
        property_obj=prop,
        action=action,
    )
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if action == "draft":
            obj.status = MaintenanceStatus.OPEN
        elif action == "start":
            obj.status = MaintenanceStatus.IN_PROGRESS
        obj.save()

        if obj.status in {MaintenanceStatus.OPEN, MaintenanceStatus.IN_PROGRESS}:
            try:
                from inventory.models import UnitStatus
                obj.unit.status = UnitStatus.MAINTENANCE
                obj.unit.save(update_fields=["status", "updated_at"])
            except Exception:
                pass
        if obj.status == MaintenanceStatus.RESOLVED:
            try:
                from inventory.models import UnitStatus
                obj.unit.status = UnitStatus.AVAILABLE
                obj.unit.save(update_fields=["status", "updated_at"])
            except Exception:
                pass

        messages.success(request, _("Maintenance ticket updated."))
        return redirect("maintenance_list")
    form_actions = [
        {"value": "draft", "label": _("Save Draft"), "class": "btn btn-sm"},
        {"value": "start", "label": _("Start Work"), "class": "btn btn-sm btn-primary"},
    ]
    is_ar = str(getattr(request, "LANGUAGE_CODE", "")).lower().startswith("ar")
    return render(
        request,
        "core/form_page.html",
        {
            "prop": prop,
            "title": (f"الخطوة 1 للصيانة - مسودة #{obj.id}" if is_ar else _("Maintenance Step 1 - Draft #%(id)s") % {"id": obj.id}),
            "form": form,
            "back_url": "maintenance_list",
            "multipart": True,
            "form_actions": form_actions,
        },
    )


@require_roles(ROLES_MAINTENANCE)
@login_required
def maintenance_complete(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(MaintenanceRequest, pk=pk, property_profile=prop)
    action = (request.POST.get("action") or "").strip()
    form = MaintenanceCompleteForm(
        request.POST or None,
        request.FILES or None,
        instance=obj,
        property_obj=prop,
        action=action,
    )
    if obj.status == MaintenanceStatus.RESOLVED:
        for field in form.fields.values():
            field.disabled = True
    if request.method == "POST" and form.is_valid():
        if obj.status == MaintenanceStatus.RESOLVED:
            return redirect("maintenance_list")
        obj = form.save(commit=False)
        if action == "finish":
            obj.status = MaintenanceStatus.RESOLVED
            if not obj.resolved_at:
                obj.resolved_at = timezone.now()
            if not obj.completed_at:
                obj.completed_at = timezone.now()
        obj.total_cost = (obj.material_cost or 0) + (obj.labor_cost or 0)
        obj.save()

        messages.success(request, _("Maintenance ticket completed."))
        return redirect("maintenance_list")

    form_actions = [] if obj.status == MaintenanceStatus.RESOLVED else [
        {"value": "finish", "label": _("Finish"), "class": "btn btn-sm btn-primary"},
    ]
    is_ar = str(getattr(request, "LANGUAGE_CODE", "")).lower().startswith("ar")
    return render(
        request,
        "core/form_page.html",
        {
            "prop": prop,
            "title": (f"الخطوة 2 للصيانة - إكمال #{obj.id}" if is_ar else _("Maintenance Step 2 - Complete #%(id)s") % {"id": obj.id}),
            "form": form,
            "back_url": "maintenance_list",
            "multipart": True,
            "form_actions": form_actions,
        },
    )


@require_roles(ROLES_HOUSEKEEPING_VIEW)
@login_required
def housekeeping_list(request):
    prop = _get_active_property(request)
    qs = HousekeepingTask.objects.select_related("unit", "assigned_to").order_by("-created_at")
    if prop:
        qs = qs.filter(property_profile=prop, unit__unit_type__business_type=prop.business_type)

    status_q = (request.GET.get("status") or "").strip()
    unit_q = (request.GET.get("unit") or "").strip()
    if status_q:
        qs = qs.filter(status=status_q)
    else:
        qs = qs.exclude(status__in=[HousekeepingStatus.DONE, HousekeepingStatus.CANCELLED])
    if unit_q:
        qs = qs.filter(unit__code__icontains=unit_q)

    can_manage = bool(request.user.is_superuser or _has_role(request.user, ROLES_ADMIN))

    staff_qs = StaffProfile.objects.filter(property=prop, is_active=True)
    housekeeping_staff = staff_qs.filter(role=StaffRole.HOUSEKEEPING).select_related("user").order_by("user__username")

    return render(
        request,
        "core/housekeeping.html",
        {
            "prop": prop,
            "tasks": qs[:500],
            "filters": {"status": status_q, "unit": unit_q},
            "can_manage": can_manage,
            "housekeeping_staff": housekeeping_staff,
        },
    )


@require_roles(ROLES_HOUSEKEEPING)
@login_required
def housekeeping_action(request, pk: int):
    prop = _get_active_property(request)
    task = get_object_or_404(HousekeepingTask, pk=pk, property_profile=prop)

    if request.method != "POST":
        return redirect("housekeeping_list")

    action = request.POST.get("action")
    staff_id = (request.POST.get("assigned_to") or "").strip()

    def _set_assignee() -> bool:
        if not staff_id:
            return False
        staff = StaffProfile.objects.filter(id=staff_id, property=prop, is_active=True).first()
        if not staff:
            messages.error(request, "Selected staff not found.")
            return False
        task.assigned_to = staff
        return True
    try:
        if action == "assign":
            if _set_assignee():
                task.save(update_fields=["assigned_to", "updated_at"])
                messages.success(request, "Task assigned.")
        elif action == "start":
            _set_assignee()
            if not task.assigned_to:
                messages.error(request, "Assign a worker before starting the task.")
                return redirect("housekeeping_list")
            task.status = HousekeepingStatus.IN_PROGRESS
            task.save(update_fields=["status", "assigned_to", "updated_at"])
            messages.success(request, "Task started.")
        elif action == "done":
            task.status = HousekeepingStatus.DONE
            task.completed_at = timezone.now()
            task.save(update_fields=["status", "completed_at", "updated_at"])
            try:
                from inventory.models import UnitStatus
                task.unit.status = UnitStatus.AVAILABLE
                task.unit.save(update_fields=["status", "updated_at"])
            except Exception:
                pass
            task.delete()
            messages.success(request, "Task marked done.")
        elif action == "maintenance":
            try:
                from inventory.models import UnitStatus
                task.unit.status = UnitStatus.MAINTENANCE
                task.unit.save(update_fields=["status", "updated_at"])
            except Exception:
                pass
            task.status = HousekeepingStatus.CANCELLED
            task.save(update_fields=["status", "updated_at"])
            task.delete()
            messages.success(request, "Room moved to maintenance. Create a ticket and assign a worker.")
            return redirect(f"{reverse('maintenance_create')}?unit={task.unit.id}")
        else:
            messages.error(request, "Unknown action.")
    except Exception as e:
        messages.error(request, f"Action failed: {e}")

    return redirect("housekeeping_list")


@require_roles(ROLES_MAINTENANCE)
@login_required
def maintenance_delete(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(MaintenanceRequest, pk=pk, property_profile=prop)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Maintenance ticket deleted.")
        return redirect("maintenance_list")
    return render(request, "core/confirm_delete.html", {"prop": prop, "title": "Delete Maintenance Ticket", "object_label": obj.title, "back_url": "maintenance_list"})

# =========================================================
# BILLING: OVERVIEW (DASHBOARD LINK TARGET)
# =========================================================
@require_roles(ROLES_BILLING)
@login_required
def billing_overview(request):
    prop = _get_active_property(request)

    invoices = Invoice.objects.select_related("guest", "booking").order_by("-created_at")
    payments = Payment.objects.select_related("invoice").order_by("-created_at")

    if prop:
        invoices = _filter_invoices_for_mode(invoices.filter(property_profile=prop), prop)
        payments = _filter_payments_for_mode(payments.filter(property_profile=prop), prop)

    return render(
        request,
        "core/billing_overview.html",
        {
            "prop": prop,
            "invoices": invoices[:10],
            "payments": payments[:10],
        },
    )


# =========================================================
# BILLING: INVOICES (CRUD)
# =========================================================
@require_roles(ROLES_BILLING)
@login_required
def invoices_list(request):
    prop = _get_active_property(request)
    qs = Invoice.objects.select_related("guest", "booking").order_by("-created_at")
    if prop:
        qs = _filter_invoices_for_mode(qs.filter(property_profile=prop), prop)
    return render(request, "core/invoices_list.html", {"prop": prop, "invoices": qs[:500]})


@require_roles(ROLES_BILLING)
@login_required
def invoice_create(request):
    prop = _get_active_property(request)
    form = InvoiceForm(request.POST or None, property_obj=prop)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.property_profile = prop
        obj.save()
        messages.success(request, _("Invoice created."))
        return redirect("invoices_list")
    return render(request, "core/form_page.html", {"prop": prop, "title": _("Add Invoice"), "form": form, "back_url": "invoices_list"})


@require_roles(ROLES_BILLING)
@login_required
def invoice_edit(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(Invoice, pk=pk, property_profile=prop)
    form = InvoiceForm(request.POST or None, instance=obj, property_obj=prop)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Invoice updated."))
        return redirect("invoices_list")
    return render(
        request,
        "core/form_page.html",
        {"prop": prop, "title": _("Edit Invoice #%(id)s") % {"id": obj.id}, "form": form, "back_url": "invoices_list"},
    )


@require_roles(ROLES_BILLING)
@login_required
def invoice_delete(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(Invoice, pk=pk, property_profile=prop)
    if request.method == "POST":
        obj.delete()
        messages.success(request, _("Invoice deleted."))
        return redirect("invoices_list")
    return render(
        request,
        "core/confirm_delete.html",
        {"prop": prop, "title": _("Delete Invoice"), "object_label": str(obj), "back_url": "invoices_list"},
    )


# =========================================================
# BILLING: PAYMENTS (CRUD)
# =========================================================
def _payments_filtered_qs(request, prop):
    qs = Payment.objects.select_related("invoice", "invoice__guest").order_by("-created_at")
    if prop:
        qs = _filter_payments_for_mode(qs.filter(property_profile=prop), prop)

    method_q = (request.GET.get("method") or "").strip()
    direction_q = (request.GET.get("direction") or "").strip()
    invoice_q = (request.GET.get("invoice") or "").strip()
    guest_q = (request.GET.get("guest") or "").strip()
    start_q = (request.GET.get("start_date") or "").strip()
    end_q = (request.GET.get("end_date") or "").strip()

    if method_q:
        qs = qs.filter(method=method_q)
    if direction_q:
        qs = qs.filter(direction=direction_q)
    if invoice_q:
        qs = qs.filter(invoice_id=invoice_q)
    if guest_q:
        qs = qs.filter(invoice__guest__full_name__icontains=guest_q)
    if start_q:
        try:
            qs = qs.filter(paid_at__date__gte=date.fromisoformat(start_q))
        except Exception:
            pass
    if end_q:
        try:
            qs = qs.filter(paid_at__date__lte=date.fromisoformat(end_q))
        except Exception:
            pass

    filters = {
        "method": method_q,
        "direction": direction_q,
        "invoice": invoice_q,
        "guest": guest_q,
        "start_date": start_q,
        "end_date": end_q,
    }
    return qs, filters


@require_roles(ROLES_BILLING)
@login_required
def payments_list(request):
    prop = _get_active_property(request)
    qs, filters = _payments_filtered_qs(request, prop)
    query = urlencode(filters)

    return render(
        request,
        "core/payments_list.html",
        {
            "prop": prop,
            "payments": qs[:500],
            "filters": filters,
            "query": query,
        },
    )


@require_roles(ROLES_BILLING)
@login_required
def payments_report_print(request):
    prop = _get_active_property(request)
    qs, filters = _payments_filtered_qs(request, prop)
    total = qs.aggregate(s=models.Sum("amount"))["s"] or Decimal("0.000")
    is_ar = (request.GET.get("lang") or "").lower() == "ar"
    query = urlencode(filters)
    back = (request.GET.get("back") or "").strip()
    is_desktop_qt = _is_desktop_qt_request(request)
    return render(
        request,
        "core/payments_report_print.html",
        {
            "prop": prop,
            "payments": qs[:2000],
            "filters": filters,
            "query": query,
            "total": total,
            "is_ar": is_ar,
            "back": back,
            "is_desktop_qt": is_desktop_qt,
        },
    )


@require_roles(ROLES_BILLING)
@login_required
def payments_report_pdf(request):
    prop = _get_active_property(request)
    qs, filters = _payments_filtered_qs(request, prop)
    is_ar = (request.GET.get("lang") or "").lower() == "ar"

    resp = HttpResponse(content_type="application/pdf")
    resp["Content-Disposition"] = "attachment; filename=payments_report_modern.pdf"
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"

    total = qs.aggregate(s=models.Sum("amount"))["s"] or Decimal("0.000")
    rows = []
    for p in qs[:2000]:
        rows.append(
            [
                f"#{p.id}",
                (p.paid_at or p.created_at).date().isoformat(),
                f"#{p.invoice_id or '-'}",
                (getattr(p.invoice.guest, "full_name", "-") if p.invoice_id else "-"),
                str(p.method),
                str(p.direction),
                str(p.amount),
            ]
        )

    title = "تقرير المدفوعات" if is_ar else "Payments Report"
    subtitle = (
        f"إجمالي السجلات: {qs.count()} | الإجمالي: {total}<br/>"
        f"الفترة: {filters.get('start_date') or '-'} - {filters.get('end_date') or '-'}"
        if is_ar
        else f"Records: {qs.count()} | Total: {total}<br/>"
        f"Period: {filters.get('start_date') or '-'} - {filters.get('end_date') or '-'}"
    )
    headers = (
        ["المعرف", "التاريخ", "الفاتورة", "الضيف", "الطريقة", "الاتجاه", "المبلغ"]
        if is_ar
        else ["ID", "Date", "Invoice", "Guest", "Method", "Direction", "Amount"]
    )
    _build_modern_pdf_report(
        resp,
        prop=prop,
        title=title,
        subtitle=subtitle,
        headers=headers,
        rows=rows,
        col_width_mm=[16, 22, 20, 38, 24, 24, 22],
        is_ar=is_ar,
    )
    return resp


@require_roles(ROLES_BILLING)
@login_required
def payments_report_excel(request):
    prop = _get_active_property(request)
    qs, _filters = _payments_filtered_qs(request, prop)
    is_ar = (request.GET.get("lang") or "").lower() == "ar"

    headers = (
        ["المعرف", "التاريخ", "الفاتورة", "الضيف", "الطريقة", "الاتجاه", "المبلغ", "المرجع", "ملغي"]
        if is_ar
        else ["ID", "Date", "Invoice", "Guest", "Method", "Direction", "Amount", "Reference", "Void"]
    )
    rows = []
    for p in qs[:5000]:
        date_str = (p.paid_at or p.created_at).date().isoformat()
        guest_name = getattr(p.invoice.guest, "full_name", "-") if p.invoice_id else "-"
        rows.append(
            [p.id, date_str, p.invoice_id or "", guest_name, p.method, p.direction, str(p.amount), p.reference or "", "yes" if p.is_void else "no"]
        )
    return _build_modern_excel_report(
        title="تقرير المدفوعات" if is_ar else "Payments Report",
        sheet_title="Payments",
        headers=headers,
        rows=rows,
        filename="payments_report_modern.xlsx",
        prop=prop,
        is_ar=is_ar,
    )


@require_roles(ROLES_ADMIN)
@login_required
def bookings_report_print(request):
    prop = _get_active_property(request)
    d1 = parse_date(request.GET.get("date_from") or "")
    d2 = parse_date(request.GET.get("date_to") or "")
    include_archived = str(request.GET.get("include_archived") or "").strip() in {"1", "true", "True", "yes", "on"}
    unit_id = request.GET.get("unit")
    if not prop or not d1 or not d2:
        messages.error(request, "Date range is required for bookings report.")
        return redirect("reports_home")

    booking_type = BookingType.HOTEL if prop.business_type == BusinessType.HOTEL else BookingType.APARTMENT
    qs = Booking.objects.select_related("unit", "guest").filter(
        property_profile=prop,
        booking_type=booking_type,
        unit__unit_type__business_type=prop.business_type,
        start_date__lt=d2,
        end_date__gt=d1,
    )
    if not include_archived:
        qs = qs.filter(is_archived=False)
    if unit_id:
        qs = qs.filter(unit_id=unit_id)
    qs = qs.order_by("-created_at")[:500]

    rows = []
    for b in qs:
        rows.append(
            {
                "id": b.id,
                "unit": getattr(b.unit, "code", str(b.unit_id)),
                "guest": getattr(b.guest, "full_name", str(b.guest_id)),
                "status": b.status,
                "start": b.start_date,
                "end": b.end_date,
                "total": b.estimate_total(),
            }
        )

    query_params = {"date_from": str(d1), "date_to": str(d2)}
    if unit_id:
        query_params["unit"] = unit_id
    if include_archived:
        query_params["include_archived"] = 1
    query = urlencode(query_params)
    is_ar = (request.GET.get("lang") or "").lower() == "ar"
    back = (request.GET.get("back") or "").strip()
    is_desktop_qt = _is_desktop_qt_request(request)
    return render(
        request,
        "core/bookings_report_print.html",
        {
            "prop": prop,
            "rows": rows,
            "d1": d1,
            "d2": d2,
            "query": query,
            "is_ar": is_ar,
            "back": back,
            "is_desktop_qt": is_desktop_qt,
        },
    )


def _maintenance_report_rows(prop, d1, d2, unit_id=None):
    qs = MaintenanceRequest.objects.select_related("unit", "assigned_to", "assigned_to__user").filter(
        property_profile=prop,
        unit__unit_type__business_type=prop.business_type,
    )
    qs = qs.filter(
        models.Q(completed_at__date__gte=d1, completed_at__date__lte=d2)
        | models.Q(resolved_at__date__gte=d1, resolved_at__date__lte=d2)
    )
    if unit_id:
        qs = qs.filter(unit_id=unit_id)
    qs = qs.order_by("-created_at")[:1000]

    rows = []
    for m in qs:
        assigned_name = ""
        if m.assigned_to and getattr(m.assigned_to, "user", None):
            assigned_name = m.assigned_to.user.username
        rows.append(
            {
                "id": m.id,
                "unit": getattr(m.unit, "code", str(m.unit_id)),
                "title": m.title or "-",
                "status": m.status,
                "priority": m.priority,
                "assigned_to": assigned_name or "-",
                "cost": m.total_cost or Decimal("0.000"),
                "completed_on": (m.completed_at or m.resolved_at or m.created_at).date(),
            }
        )
    return rows


def _occupancy_report_rows(prop, d1, d2, unit=None, include_archived=False):
    units_qs = Unit.objects.filter(
        property_profile=prop,
        is_active=True,
        unit_type__business_type=prop.business_type,
    ).order_by("code")
    if unit:
        units_qs = units_qs.filter(id=unit.id)
    units = list(units_qs)

    booking_type = _current_booking_type(prop)
    bookings_qs = Booking.objects.select_related("unit").filter(
        property_profile=prop,
        booking_type=booking_type,
        unit__unit_type__business_type=prop.business_type,
        start_date__lte=d2,
        end_date__gte=d1,
    ).exclude(status__in=[BookingStatus.CANCELLED, BookingStatus.NO_SHOW])
    if not include_archived:
        bookings_qs = bookings_qs.filter(is_archived=False)
    if unit:
        bookings_qs = bookings_qs.filter(unit=unit)
    bookings_by_unit = {}
    for b in bookings_qs:
        bookings_by_unit.setdefault(b.unit_id, []).append(b)

    total_nights = max((d2 - d1).days, 1)
    rows = []
    for u in units:
        booked_nights = 0
        for b in bookings_by_unit.get(u.id, []):
            overlap_start = max(b.start_date, d1)
            overlap_end = min(b.end_date, d2)
            booked_nights += max((overlap_end - overlap_start).days, 0)
        occupancy_pct = round((booked_nights / total_nights) * 100.0, 2) if total_nights > 0 else 0.0
        rows.append(
            {
                "unit": u.code,
                "booked_nights": booked_nights,
                "total_nights": total_nights,
                "occupancy_pct": occupancy_pct,
            }
        )
    return rows


@require_roles(ROLES_ADMIN)
@login_required
def occupancy_report_print(request):
    prop = _get_active_property(request)
    d1 = parse_date(request.GET.get("start_date") or request.GET.get("date_from") or "")
    d2 = parse_date(request.GET.get("end_date") or request.GET.get("date_to") or "")
    unit_id = request.GET.get("unit")
    include_archived = str(request.GET.get("include_archived") or "").strip() in {"1", "true", "True", "yes", "on"}
    if not prop or not d1 or not d2:
        messages.error(request, "Date range is required for occupancy report.")
        return redirect("reports_home")

    unit = Unit.objects.filter(id=unit_id, property_profile=prop).first() if unit_id else None
    rows = _occupancy_report_rows(prop, d1, d2, unit=unit, include_archived=include_archived)
    avg_occupancy = round(sum(r["occupancy_pct"] for r in rows) / len(rows), 2) if rows else 0.0
    query_params = {"start_date": str(d1), "end_date": str(d2)}
    if unit_id:
        query_params["unit"] = unit_id
    if include_archived:
        query_params["include_archived"] = 1
    query = urlencode(query_params)
    is_ar = (request.GET.get("lang") or "").lower() == "ar"
    back = (request.GET.get("back") or "").strip()
    is_desktop_qt = _is_desktop_qt_request(request)
    return render(
        request,
        "core/occupancy_report_print.html",
        {
            "prop": prop,
            "rows": rows,
            "d1": d1,
            "d2": d2,
            "query": query,
            "is_ar": is_ar,
            "avg_occupancy": avg_occupancy,
            "back": back,
            "is_desktop_qt": is_desktop_qt,
        },
    )


@require_roles(ROLES_ADMIN)
@login_required
def occupancy_report_pdf(request):
    prop = _get_active_property(request)
    d1 = parse_date(request.GET.get("start_date") or request.GET.get("date_from") or "")
    d2 = parse_date(request.GET.get("end_date") or request.GET.get("date_to") or "")
    unit_id = request.GET.get("unit")
    include_archived = str(request.GET.get("include_archived") or "").strip() in {"1", "true", "True", "yes", "on"}
    if not prop or not d1 or not d2:
        return HttpResponse("Date range is required.", status=400)

    unit = Unit.objects.filter(id=unit_id, property_profile=prop).first() if unit_id else None
    rows = _occupancy_report_rows(prop, d1, d2, unit=unit, include_archived=include_archived)[:500]
    avg_occupancy = round(sum(r["occupancy_pct"] for r in rows) / len(rows), 2) if rows else 0.0
    is_ar = (request.GET.get("lang") or "").lower() == "ar"

    resp = HttpResponse(content_type="application/pdf")
    resp["Content-Disposition"] = "attachment; filename=occupancy_report_modern.pdf"
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    data_rows = [[str(r["unit"]), str(r["booked_nights"]), str(r["total_nights"]), f'{r["occupancy_pct"]}%'] for r in rows]
    title = "تقرير الإشغال" if is_ar else "Occupancy Report"
    subtitle = (
        f"الوحدات: {len(rows)} | متوسط الإشغال: {avg_occupancy}%<br/>الفترة: {d1} - {d2}"
        if is_ar
        else f"Units: {len(rows)} | Avg Occupancy: {avg_occupancy}%<br/>Period: {d1} - {d2}"
    )
    headers = ["الوحدة", "الليالي المحجوزة", "إجمالي الليالي", "نسبة الإشغال"] if is_ar else ["Unit", "Booked Nights", "Total Nights", "Occupancy %"]
    _build_modern_pdf_report(
        resp,
        prop=prop,
        title=title,
        subtitle=subtitle,
        headers=headers,
        rows=data_rows,
        col_width_mm=[36, 44, 44, 44],
        is_ar=is_ar,
    )
    return resp


@require_roles(ROLES_ADMIN)
@login_required
def occupancy_report_excel(request):
    prop = _get_active_property(request)
    d1 = parse_date(request.GET.get("start_date") or request.GET.get("date_from") or "")
    d2 = parse_date(request.GET.get("end_date") or request.GET.get("date_to") or "")
    unit_id = request.GET.get("unit")
    include_archived = str(request.GET.get("include_archived") or "").strip() in {"1", "true", "True", "yes", "on"}
    if not prop or not d1 or not d2:
        return HttpResponse("Date range is required.", status=400)

    unit = Unit.objects.filter(id=unit_id, property_profile=prop).first() if unit_id else None
    rows = _occupancy_report_rows(prop, d1, d2, unit=unit, include_archived=include_archived)
    is_ar = (request.GET.get("lang") or "").lower() == "ar"
    headers = ["الوحدة", "الليالي المحجوزة", "إجمالي الليالي", "نسبة الإشغال %"] if is_ar else ["Unit", "Booked Nights", "Total Nights", "Occupancy %"]
    data_rows = [[r["unit"], r["booked_nights"], r["total_nights"], r["occupancy_pct"]] for r in rows]
    return _build_modern_excel_report(
        title="تقرير الإشغال" if is_ar else "Occupancy Report",
        sheet_title="Occupancy",
        headers=headers,
        rows=data_rows,
        filename="occupancy_report_modern.xlsx",
        prop=prop,
        is_ar=is_ar,
    )


@require_roles(ROLES_ADMIN)
@login_required
def maintenance_report_print(request):
    prop = _get_active_property(request)
    d1 = parse_date(request.GET.get("start_date") or request.GET.get("date_from") or "")
    d2 = parse_date(request.GET.get("end_date") or request.GET.get("date_to") or "")
    unit_id = request.GET.get("unit")
    if not prop or not d1 or not d2:
        messages.error(request, "Date range is required for maintenance report.")
        return redirect("reports_home")

    rows = _maintenance_report_rows(prop, d1, d2, unit_id=unit_id)
    total_cost = sum((r["cost"] for r in rows), Decimal("0.000"))
    query_params = {"start_date": str(d1), "end_date": str(d2)}
    if unit_id:
        query_params["unit"] = unit_id
    query = urlencode(query_params)
    is_ar = (request.GET.get("lang") or "").lower() == "ar"
    back = (request.GET.get("back") or "").strip()
    is_desktop_qt = _is_desktop_qt_request(request)
    return render(
        request,
        "core/maintenance_report_print.html",
        {
            "prop": prop,
            "rows": rows,
            "d1": d1,
            "d2": d2,
            "query": query,
            "is_ar": is_ar,
            "total_cost": total_cost,
            "back": back,
            "is_desktop_qt": is_desktop_qt,
        },
    )


@require_roles(ROLES_ADMIN)
@login_required
def maintenance_report_pdf(request):
    prop = _get_active_property(request)
    d1 = parse_date(request.GET.get("start_date") or request.GET.get("date_from") or "")
    d2 = parse_date(request.GET.get("end_date") or request.GET.get("date_to") or "")
    unit_id = request.GET.get("unit")
    if not prop or not d1 or not d2:
        return HttpResponse("Date range is required.", status=400)

    rows = _maintenance_report_rows(prop, d1, d2, unit_id=unit_id)[:300]
    total_cost = sum((r["cost"] for r in rows), Decimal("0.000"))
    is_ar = (request.GET.get("lang") or "").lower() == "ar"

    resp = HttpResponse(content_type="application/pdf")
    resp["Content-Disposition"] = "attachment; filename=maintenance_report_modern.pdf"
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    data_rows = [
        [
            f"#{r['id']}",
            str(r["unit"]),
            str(r["title"]),
            str(r["status"]),
            str(r["priority"]),
            str(r["assigned_to"]),
            str(r["completed_on"]),
            str(r["cost"]),
        ]
        for r in rows
    ]
    title = "تقرير الصيانة" if is_ar else "Maintenance Report"
    subtitle = (
        f"السجلات: {len(rows)} | التكلفة الإجمالية: {total_cost}<br/>الفترة: {d1} - {d2}"
        if is_ar
        else f"Records: {len(rows)} | Total Cost: {total_cost}<br/>Period: {d1} - {d2}"
    )
    headers = (
        ["المعرف", "الوحدة", "العنوان", "الحالة", "الأولوية", "المسند إليه", "التاريخ", "التكلفة"]
        if is_ar
        else ["ID", "Unit", "Title", "Status", "Priority", "Assigned", "Date", "Cost"]
    )
    _build_modern_pdf_report(
        resp,
        prop=prop,
        title=title,
        subtitle=subtitle,
        headers=headers,
        rows=data_rows,
        col_width_mm=[14, 18, 40, 22, 20, 26, 22, 20],
        is_ar=is_ar,
    )
    return resp


@require_roles(ROLES_ADMIN)
@login_required
def maintenance_report_excel(request):
    prop = _get_active_property(request)
    d1 = parse_date(request.GET.get("start_date") or request.GET.get("date_from") or "")
    d2 = parse_date(request.GET.get("end_date") or request.GET.get("date_to") or "")
    unit_id = request.GET.get("unit")
    if not prop or not d1 or not d2:
        return HttpResponse("Date range is required.", status=400)

    rows = _maintenance_report_rows(prop, d1, d2, unit_id=unit_id)
    is_ar = (request.GET.get("lang") or "").lower() == "ar"
    headers = (
        ["المعرف", "الوحدة", "العنوان", "الحالة", "الأولوية", "المسند إليه", "التاريخ", "التكلفة"]
        if is_ar
        else ["ID", "Unit", "Title", "Status", "Priority", "Assigned", "Date", "Cost"]
    )
    data_rows = [[r["id"], r["unit"], r["title"], r["status"], r["priority"], r["assigned_to"], str(r["completed_on"]), str(r["cost"])] for r in rows]
    return _build_modern_excel_report(
        title="تقرير الصيانة" if is_ar else "Maintenance Report",
        sheet_title="Maintenance",
        headers=headers,
        rows=data_rows,
        filename="maintenance_report_modern.xlsx",
        prop=prop,
        is_ar=is_ar,
    )


def _revenue_report_rows(prop, d1, d2, unit=None, include_archived=False):
    qs = Invoice.objects.select_related("guest", "booking", "booking__unit").filter(
        property_profile=prop,
        created_at__date__gte=d1,
        created_at__date__lte=d2,
    )
    qs = _filter_invoices_for_mode(qs, prop)
    if unit:
        qs = qs.filter(booking__unit=unit)
    if not include_archived:
        qs = qs.exclude(booking__is_archived=True)
    qs = qs.order_by("-created_at")[:3000]

    rows = []
    for inv in qs:
        rows.append(
            {
                "id": inv.id,
                "date": inv.created_at.date(),
                "guest": getattr(inv.guest, "full_name", "-"),
                "unit": getattr(getattr(inv.booking, "unit", None), "code", "-"),
                "status": inv.status,
                "subtotal": inv.subtotal or Decimal("0.000"),
                "tax": inv.tax_total or Decimal("0.000"),
                "total": inv.total or Decimal("0.000"),
                "paid": inv.amount_paid or Decimal("0.000"),
                "balance": inv.balance_due or Decimal("0.000"),
            }
        )
    return rows


@require_roles(ROLES_ADMIN)
@login_required
def revenue_report_print(request):
    prop = _get_active_property(request)
    d1 = parse_date(request.GET.get("start_date") or request.GET.get("date_from") or "")
    d2 = parse_date(request.GET.get("end_date") or request.GET.get("date_to") or "")
    unit_id = request.GET.get("unit")
    include_archived = str(request.GET.get("include_archived") or "").strip() in {"1", "true", "True", "yes", "on"}
    if not prop or not d1 or not d2:
        messages.error(request, "Date range is required for revenue report.")
        return redirect("reports_home")

    unit = Unit.objects.filter(id=unit_id, property_profile=prop).first() if unit_id else None
    rows = _revenue_report_rows(prop, d1, d2, unit=unit, include_archived=include_archived)
    total_revenue = sum((r["total"] for r in rows), Decimal("0.000"))
    total_paid = sum((r["paid"] for r in rows), Decimal("0.000"))
    total_balance = sum((r["balance"] for r in rows), Decimal("0.000"))
    query_params = {"start_date": str(d1), "end_date": str(d2)}
    if unit_id:
        query_params["unit"] = unit_id
    if include_archived:
        query_params["include_archived"] = 1
    query = urlencode(query_params)
    is_ar = (request.GET.get("lang") or "").lower() == "ar"
    back = (request.GET.get("back") or "").strip()
    is_desktop_qt = _is_desktop_qt_request(request)
    return render(
        request,
        "core/revenue_report_print.html",
        {
            "prop": prop,
            "rows": rows,
            "d1": d1,
            "d2": d2,
            "query": query,
            "is_ar": is_ar,
            "total_revenue": total_revenue,
            "total_paid": total_paid,
            "total_balance": total_balance,
            "back": back,
            "is_desktop_qt": is_desktop_qt,
        },
    )


@require_roles(ROLES_ADMIN)
@login_required
def revenue_report_pdf(request):
    prop = _get_active_property(request)
    d1 = parse_date(request.GET.get("start_date") or request.GET.get("date_from") or "")
    d2 = parse_date(request.GET.get("end_date") or request.GET.get("date_to") or "")
    unit_id = request.GET.get("unit")
    include_archived = str(request.GET.get("include_archived") or "").strip() in {"1", "true", "True", "yes", "on"}
    if not prop or not d1 or not d2:
        return HttpResponse("Date range is required.", status=400)

    unit = Unit.objects.filter(id=unit_id, property_profile=prop).first() if unit_id else None
    rows = _revenue_report_rows(prop, d1, d2, unit=unit, include_archived=include_archived)[:300]
    total_revenue = sum((r["total"] for r in rows), Decimal("0.000"))
    total_paid = sum((r["paid"] for r in rows), Decimal("0.000"))
    total_balance = sum((r["balance"] for r in rows), Decimal("0.000"))
    is_ar = (request.GET.get("lang") or "").lower() == "ar"

    resp = HttpResponse(content_type="application/pdf")
    resp["Content-Disposition"] = "attachment; filename=revenue_report_modern.pdf"
    resp["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    data_rows = [
        [
            f"#{r['id']}",
            str(r["date"]),
            str(r["guest"]),
            str(r["unit"]),
            str(r["status"]),
            str(r["subtotal"]),
            str(r["tax"]),
            str(r["total"]),
            str(r["balance"]),
        ]
        for r in rows
    ]
    title = "تقرير الإيرادات" if is_ar else "Revenue Report"
    subtitle = (
        f"السجلات: {len(rows)} | الإيراد: {total_revenue} | المدفوع: {total_paid} | المتبقي: {total_balance}<br/>الفترة: {d1} - {d2}"
        if is_ar
        else f"Records: {len(rows)} | Revenue: {total_revenue} | Paid: {total_paid} | Balance: {total_balance}<br/>Period: {d1} - {d2}"
    )
    headers = (
        ["المعرف", "التاريخ", "الضيف", "الوحدة", "الحالة", "الإجمالي الفرعي", "الضريبة", "الإجمالي", "المتبقي"]
        if is_ar
        else ["ID", "Date", "Guest", "Unit", "Status", "Subtotal", "Tax", "Total", "Balance"]
    )
    _build_modern_pdf_report(
        resp,
        prop=prop,
        title=title,
        subtitle=subtitle,
        headers=headers,
        rows=data_rows,
        col_width_mm=[12, 20, 36, 14, 18, 22, 16, 18, 18],
        is_ar=is_ar,
    )
    return resp


@require_roles(ROLES_ADMIN)
@login_required
def revenue_report_excel(request):
    prop = _get_active_property(request)
    d1 = parse_date(request.GET.get("start_date") or request.GET.get("date_from") or "")
    d2 = parse_date(request.GET.get("end_date") or request.GET.get("date_to") or "")
    unit_id = request.GET.get("unit")
    include_archived = str(request.GET.get("include_archived") or "").strip() in {"1", "true", "True", "yes", "on"}
    if not prop or not d1 or not d2:
        return HttpResponse("Date range is required.", status=400)

    unit = Unit.objects.filter(id=unit_id, property_profile=prop).first() if unit_id else None
    rows = _revenue_report_rows(prop, d1, d2, unit=unit, include_archived=include_archived)
    is_ar = (request.GET.get("lang") or "").lower() == "ar"
    headers = (
        ["المعرف", "التاريخ", "الضيف", "الوحدة", "الحالة", "الإجمالي الفرعي", "الضريبة", "الإجمالي", "المدفوع", "المتبقي"]
        if is_ar
        else ["ID", "Date", "Guest", "Unit", "Status", "Subtotal", "Tax", "Total", "Paid", "Balance"]
    )
    data_rows = [
        [r["id"], str(r["date"]), r["guest"], r["unit"], r["status"], str(r["subtotal"]), str(r["tax"]), str(r["total"]), str(r["paid"]), str(r["balance"])]
        for r in rows
    ]
    return _build_modern_excel_report(
        title="تقرير الإيرادات" if is_ar else "Revenue Report",
        sheet_title="Revenue",
        headers=headers,
        rows=data_rows,
        filename="revenue_report_modern.xlsx",
        prop=prop,
        is_ar=is_ar,
    )


@require_roles(ROLES_BILLING)
@login_required
def payment_create(request):
    prop = _get_active_property(request)
    form = PaymentForm(request.POST or None, property_obj=prop)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.property_profile = prop
        obj.save()
        messages.success(request, _("Payment created."))
        return redirect("payments_list")
    return render(request, "core/form_page.html", {"prop": prop, "title": _("Add Payment"), "form": form, "back_url": "payments_list"})


@require_roles(ROLES_BILLING)
@login_required
def payment_edit(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(Payment, pk=pk, property_profile=prop)
    form = PaymentForm(request.POST or None, instance=obj, property_obj=prop)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Payment updated."))
        return redirect("payments_list")
    return render(request, "core/form_page.html", {"prop": prop, "title": _("Edit Payment #%(id)s") % {"id": obj.id}, "form": form, "back_url": "payments_list"})


@require_roles(ROLES_BILLING)
@login_required
def payment_delete(request, pk: int):
    prop = _get_active_property(request)
    obj = get_object_or_404(Payment, pk=pk, property_profile=prop)
    if request.method == "POST":
        obj.delete()
        messages.success(request, _("Payment deleted."))
        return redirect("payments_list")
    return render(request, "core/confirm_delete.html", {"prop": prop, "title": "Delete Payment", "object_label": f"Payment #{obj.id}", "back_url": "payments_list"})


# =========================================================
# PRICING + REPORTS + SETTINGS (keep existing)
# =========================================================
@require_roles(ROLES_ADMIN)
@login_required
def rateplans_list(request):
    prop = _get_active_property(request)

    form = RatePlanForm(request.POST or None, property_obj=prop)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if prop and hasattr(obj, "property_profile_id"):
            obj.property_profile = prop
        obj.save()
        messages.success(request, "Rate plan saved.")
        return redirect("rateplans_list")

    qs = RatePlan.objects.all().order_by("-created_at")
    if prop:
        qs = _filter_rateplans_for_mode(qs.filter(property_profile=prop), prop)

    return render(request, "core/pricing_rateplans.html", {"prop": prop, "form": form, "items": qs[:200]})


@require_roles(ROLES_ADMIN)
@login_required
def seasonalrates_list(request):
    prop = _get_active_property(request)

    form = SeasonalRateRuleForm(request.POST or None, property_obj=prop)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if prop and hasattr(obj, "property_profile_id"):
            obj.property_profile = prop
        obj.save()
        messages.success(request, "Seasonal rule saved.")
        return redirect("seasonalrates_list")

    qs = SeasonalRateRule.objects.select_related("rate_plan").all().order_by("-priority", "-created_at")
    if prop:
        qs = _filter_rules_for_mode(qs.filter(property_profile=prop), prop)

    return render(request, "core/pricing_seasonal.html", {"prop": prop, "form": form, "items": qs[:200]})


@require_roles(ROLES_ADMIN)
@login_required
def reports_home(request):
    prop = _get_active_property(request)
    form = ReportsForm(request.GET or None, property_obj=prop)

    occupancy = None
    export_links = None
    summary = None
    charts = None
    selected_report_type = (request.GET.get("report_type") or "revenue").strip() or "revenue"
    if selected_report_type not in {"revenue", "occupancy", "maintenance", "payments"}:
        selected_report_type = "revenue"

    if form.is_valid():
        period = form.cleaned_data.get("period") or "custom"
        report_type = form.cleaned_data.get("report_type") or "revenue"
        selected_report_type = report_type
        unit = form.cleaned_data.get("unit")
        include_archived = bool(form.cleaned_data.get("include_archived"))

        today = timezone.localdate()
        d1 = form.cleaned_data.get("date_from")
        d2 = form.cleaned_data.get("date_to")

        if period == "weekly" and not (d1 and d2):
            d2 = today
            d1 = d2 - timedelta(days=6)
        if period == "daily" and not (d1 and d2):
            d2 = today
            d1 = d2
        if period == "monthly" and not (d1 and d2):
            d2 = today
            d1 = d2 - timedelta(days=29)

        if d1 and d2:
            # Occupancy
            units_qs = Unit.objects.filter(property_profile=prop, is_active=True, unit_type__business_type=prop.business_type)
            if unit:
                units_qs = units_qs.filter(id=unit.id)
            total_units = units_qs.count()
            total_unit_nights = total_units * max((d2 - d1).days, 1)

            booking_type = _current_booking_type(prop)
            bookings_qs = Booking.objects.filter(
                property_profile=prop,
                booking_type=booking_type,
                unit__unit_type__business_type=prop.business_type,
            ).exclude(
                status__in=[BookingStatus.CANCELLED, BookingStatus.NO_SHOW]
            ).filter(start_date__lte=d2, end_date__gte=d1)
            if not include_archived:
                bookings_qs = bookings_qs.filter(is_archived=False)
            if unit:
                bookings_qs = bookings_qs.filter(unit=unit)

            booked_nights = 0
            for b in bookings_qs.only("start_date", "end_date"):
                overlap_start = max(b.start_date, d1)
                overlap_end = min(b.end_date, d2)
                booked_nights += max((overlap_end - overlap_start).days, 0)

            occupancy_pct = 0.0
            if total_unit_nights > 0:
                occupancy_pct = round((booked_nights / total_unit_nights) * 100.0, 2)

            # Revenue + payments
            inv_qs = Invoice.objects.filter(property_profile=prop, created_at__date__gte=d1, created_at__date__lte=d2)
            inv_qs = _filter_invoices_for_mode(inv_qs, prop)
            if unit:
                inv_qs = inv_qs.filter(booking__unit=unit)
            if not include_archived:
                inv_qs = inv_qs.exclude(booking__is_archived=True)
            revenue_total = inv_qs.aggregate(s=models.Sum("total"))["s"] or Decimal("0.000")
            outstanding_total = inv_qs.aggregate(s=models.Sum("balance_due"))["s"] or Decimal("0.000")

            pay_qs = Payment.objects.filter(property_profile=prop, is_void=False, created_at__date__gte=d1, created_at__date__lte=d2)
            pay_qs = _filter_payments_for_mode(pay_qs, prop)
            if unit:
                pay_qs = pay_qs.filter(invoice__booking__unit=unit)
            collections_total = (
                pay_qs.filter(direction=PaymentDirection.IN).aggregate(s=models.Sum("amount"))["s"] or Decimal("0.000")
            )
            payments_count = pay_qs.count()

            # Maintenance costs
            m_qs = MaintenanceRequest.objects.filter(property_profile=prop)
            m_qs = m_qs.filter(models.Q(completed_at__date__gte=d1, completed_at__date__lte=d2) | models.Q(resolved_at__date__gte=d1, resolved_at__date__lte=d2))
            m_qs = m_qs.filter(unit__unit_type__business_type=prop.business_type)
            if unit:
                m_qs = m_qs.filter(unit=unit)
            maintenance_total = m_qs.aggregate(s=models.Sum("total_cost"))["s"] or Decimal("0.000")
            maintenance_count = m_qs.count()

            net_income = revenue_total - maintenance_total

            # Unit status snapshot
            units_by_status = units_qs.values("status").annotate(count=models.Count("id"))
            units_by_status_map = {row["status"]: row["count"] for row in units_by_status}

            summary = {
                "date_from": d1,
                "date_to": d2,
                "occupancy_pct": occupancy_pct,
                "booked_nights": booked_nights,
                "total_unit_nights": total_unit_nights,
                "revenue_total": revenue_total,
                "collections_total": collections_total,
                "payments_count": payments_count,
                "outstanding_total": outstanding_total,
                "maintenance_total": maintenance_total,
                "maintenance_count": maintenance_count,
                "net_income": net_income,
                "units": units_by_status_map,
            }

            rev_values = [float(revenue_total), float(maintenance_total), float(net_income)]
            max_rev = max([abs(v) for v in rev_values]) if rev_values else 0.0
            if max_rev <= 0:
                max_rev = 1.0

            if report_type == "payments":
                charts_rows = [
                    {"label": "Collections", "value": float(collections_total), "pct": round((abs(float(collections_total)) / max_rev) * 100.0, 2)},
                    {"label": "Outstanding", "value": float(outstanding_total), "pct": round((abs(float(outstanding_total)) / max_rev) * 100.0, 2)},
                    {"label": "Revenue", "value": float(revenue_total), "pct": round((abs(float(revenue_total)) / max_rev) * 100.0, 2)},
                ]
            elif report_type == "occupancy":
                total_nights_val = float(total_unit_nights or 0)
                booked_nights_val = float(booked_nights or 0)
                available_nights_val = max(total_nights_val - booked_nights_val, 0.0)
                occ_base = max(total_nights_val, 1.0)
                charts_rows = [
                    {"label": "Booked Nights", "value": booked_nights_val, "pct": round((booked_nights_val / occ_base) * 100.0, 2)},
                    {"label": "Available Nights", "value": available_nights_val, "pct": round((available_nights_val / occ_base) * 100.0, 2)},
                    {"label": "Total Nights", "value": total_nights_val, "pct": 100.0},
                ]
            elif report_type == "maintenance":
                charts_rows = [
                    {"label": "Maintenance", "value": float(maintenance_total), "pct": round((abs(float(maintenance_total)) / max_rev) * 100.0, 2)},
                    {"label": "Revenue", "value": float(revenue_total), "pct": round((abs(float(revenue_total)) / max_rev) * 100.0, 2)},
                    {"label": "Net", "value": float(net_income), "pct": round((abs(float(net_income)) / max_rev) * 100.0, 2)},
                ]
            else:
                charts_rows = [
                    {"label": "Revenue", "value": float(revenue_total), "pct": round((abs(float(revenue_total)) / max_rev) * 100.0, 2)},
                    {"label": "Maintenance", "value": float(maintenance_total), "pct": round((abs(float(maintenance_total)) / max_rev) * 100.0, 2)},
                    {"label": "Net", "value": float(net_income), "pct": round((abs(float(net_income)) / max_rev) * 100.0, 2)},
                ]

            charts = {"revenue": charts_rows, "occupancy": occupancy_pct}

            occupancy = {"api_url": f"/api/reports/occupancy/?property_profile={prop.id}&start_date={d1}&end_date={d2}"}
            lang_code = (getattr(request, "LANGUAGE_CODE", "en") or "en")[:2]
            export_params = {
                "property_profile": prop.id,
                "date_from": d1,
                "date_to": d2,
                "lang": lang_code,
                "report_type": report_type,
            }
            if unit:
                export_params["unit"] = unit.id
            if include_archived:
                export_params["include_archived"] = 1
            export_qs = urlencode(export_params)

            if report_type == "revenue":
                export_links = {
                    "print": f"/reports/revenue/print/?start_date={d1}&end_date={d2}&lang={lang_code}{f'&unit={unit.id}' if unit else ''}{'&include_archived=1' if include_archived else ''}",
                    "xlsx": f"/reports/revenue/excel/?start_date={d1}&end_date={d2}&lang={lang_code}{f'&unit={unit.id}' if unit else ''}{'&include_archived=1' if include_archived else ''}",
                    "pdf": f"/reports/revenue/pdf/?start_date={d1}&end_date={d2}&lang={lang_code}{f'&unit={unit.id}' if unit else ''}{'&include_archived=1' if include_archived else ''}",
                }
            elif report_type == "payments":
                export_links = {
                    "print": f"/billing/payments/report/print/?start_date={d1}&end_date={d2}&lang={lang_code}",
                    "xlsx": f"/billing/payments/report/excel/?start_date={d1}&end_date={d2}&lang={lang_code}",
                    "pdf": f"/billing/payments/report/pdf/?start_date={d1}&end_date={d2}&lang={lang_code}",
                }
            elif report_type == "maintenance":
                export_links = {
                    "print": f"/reports/maintenance/print/?date_from={d1}&date_to={d2}&lang={lang_code}{f'&unit={unit.id}' if unit else ''}",
                    "xlsx": f"/reports/maintenance/excel/?date_from={d1}&date_to={d2}&lang={lang_code}{f'&unit={unit.id}' if unit else ''}",
                    "pdf": f"/reports/maintenance/pdf/?date_from={d1}&date_to={d2}&lang={lang_code}{f'&unit={unit.id}' if unit else ''}",
                }
            elif report_type == "occupancy":
                export_links = {
                    "print": f"/reports/occupancy/print/?start_date={d1}&end_date={d2}&lang={lang_code}{f'&unit={unit.id}' if unit else ''}{'&include_archived=1' if include_archived else ''}",
                    "xlsx": f"/reports/occupancy/excel/?start_date={d1}&end_date={d2}&lang={lang_code}{f'&unit={unit.id}' if unit else ''}{'&include_archived=1' if include_archived else ''}",
                    "pdf": f"/reports/occupancy/pdf/?start_date={d1}&end_date={d2}&lang={lang_code}{f'&unit={unit.id}' if unit else ''}{'&include_archived=1' if include_archived else ''}",
                }
            else:
                export_links = {
                    "print": f"/reports/bookings/print/?{export_qs}",
                    "xlsx": f"/api/reports/export-bookings.xlsx?{export_qs}",
                    "pdf": f"/api/reports/export-bookings.pdf?{export_qs}",
                }

    return render(
        request,
        "core/reports.html",
        {
            "prop": prop,
            "form": form,
            "occupancy": occupancy,
            "exports": export_links,
            "summary": summary,
            "charts": charts,
            "selected_report_type": selected_report_type,
        },
    )


def _db_form_initial(profile: DatabaseConnection | None) -> dict:
    if not profile:
        return {
            "host": "",
            "port": "5432",
            "db_name": "",
            "username": "",
            "sslmode": "require",
        }
    return {
        "host": profile.host,
        "port": profile.port,
        "db_name": profile.db_name,
        "username": profile.username,
        "sslmode": profile.sslmode,
    }


def _build_db_config(cleaned: dict, password: str) -> dict:
    config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": cleaned.get("db_name") or "",
        "USER": cleaned.get("username") or "",
        "PASSWORD": password or "",
        "HOST": cleaned.get("host") or "",
        "PORT": cleaned.get("port") or "5432",
    }
    sslmode = cleaned.get("sslmode") or "require"
    if sslmode:
        config["OPTIONS"] = {"sslmode": sslmode}
    return config


def _test_db_connection(db_config: dict) -> tuple[bool, str | None]:
    alias = "external_pg"
    try:
        connections.databases[alias] = db_config
        conn = connections[alias]
        conn.ensure_connection()
        return True, None
    except Exception as e:
        return False, str(e)
    finally:
        try:
            conn = connections[alias]
            conn.close()
        except Exception:
            pass
        connections.databases.pop(alias, None)


@require_roles(ROLES_ADMIN)
@login_required
def settings_page(request):
    prop = _get_active_property(request)
    all_properties = list(PropertyProfile.objects.order_by("name_en", "id"))
    if prop is None and all_properties:
        prop = all_properties[0]
        request.session["active_property_id"] = prop.id
    can_manage_properties = _can_manage_properties(request.user)
    tier_names = ["Standard", "Premium", "Deluxe", "Luxury"]
    tier_presets = {
        "hotel": {
            "Standard": [
                "Comfortable bed and basic linens",
                "Air conditioning / Heating",
                "TV (local channels)",
                "Wardrobe / closet",
                "Work desk or side table",
                "Free Wi-Fi",
                "Shower bathroom",
                "Basic toiletries (soap, shampoo)",
                "Towels",
                "Daily or alternate-day housekeeping",
                "Front desk / reception support",
            ],
            "Premium": [
                "Larger room or improved layout",
                "Smart TV / international channels",
                "Mini fridge",
                "Coffee and tea maker",
                "Iron and ironing board",
                "Hair dryer",
                "Better-quality toiletries",
                "Faster Wi-Fi",
                "Daily housekeeping",
                "Limited room service",
            ],
            "Deluxe": [
                "Premium mattress and bedding",
                "Seating area / sofa",
                "Balcony or city/sea view",
                "Work desk with ergonomic chair",
                "Bathtub or rain shower",
                "Bathrobes and slippers",
                "Premium toiletries",
                "Priority check-in / late check-out (subject to availability)",
                "Concierge assistance",
                "Extended room service",
            ],
            "Luxury": [
                "Suite or luxury room layout",
                "Designer furniture",
                "Panoramic views",
                "Private balcony or terrace",
                "Jacuzzi / spa bathtub",
                "Luxury bath products",
                "Smart room controls (lights, AC, curtains)",
                "Complimentary minibar",
                "Personal concierge",
                "Airport pickup and drop-off",
                "Daily turndown service",
                "Access to spa, gym, pool and lounge",
            ],
        },
        "apartments": {
            "Standard": [
                "Furnished bedroom",
                "Living area (basic seating)",
                "Air conditioning",
                "TV",
                "Free Wi-Fi",
                "Compact kitchenette",
                "Refrigerator",
                "Basic cookware and utensils",
                "Shower bathroom",
                "Basic toiletries",
                "Weekly housekeeping",
            ],
            "Premium": [
                "Spacious living area",
                "Smart TV",
                "Dedicated dining space",
                "Fully equipped kitchen",
                "Microwave and electric stove",
                "Washing machine",
                "Iron and ironing board",
                "Hair dryer",
                "Faster Wi-Fi",
                "Housekeeping 2-3 times per week",
            ],
            "Deluxe": [
                "Large living and dining area",
                "Balcony",
                "Premium furniture",
                "Full kitchen with oven",
                "Dishwasher",
                "Washing machine and dryer",
                "Bathtub or rain shower",
                "Premium toiletries",
                "Weekly deep cleaning",
                "Dedicated guest support",
            ],
            "Luxury": [
                "Luxury or penthouse apartment",
                "Designer interiors",
                "Panoramic views",
                "Private terrace",
                "Smart home automation",
                "Jacuzzi or spa bath",
                "High-end kitchen appliances",
                "Complimentary minibar",
                "Personal concierge",
                "Airport transfers",
                "Daily housekeeping",
                "Access to gym, pool and spa",
            ],
        },
    }

    form = PropertyProfileForm(request.POST or None, request.FILES or None, instance=prop)
    amenity_form_prefix = "amenity"
    amenity_form = AmenityForm(
        request.POST if request.method == "POST" and request.POST.get("form_kind") == "amenity_add" else None,
        prefix=amenity_form_prefix, property_obj=prop,
    )
    amenities = Amenity.objects.filter(property_profile=prop).order_by("name_en") if prop else Amenity.objects.none()
    # Provide Arabic fallback values for amenities with empty `name_ar` so the form inputs show Arabic.
    amenity_translations_fallback = AMENITY_AR_NAMES
    if amenities:
        for a in amenities:
            if not a.name_ar:
                a.name_ar = amenity_translations_fallback.get(a.name_en, "")
    # After ensuring DB rows exist, re-fetch amenities and apply Arabic fallbacks again
    amenities = Amenity.objects.filter(property_profile=prop).order_by("name_en") if prop else Amenity.objects.none()
    if amenities:
        for a in amenities:
            if not a.name_ar:
                a.name_ar = amenity_translations_fallback.get(a.name_en, "")

    db_profile = DatabaseConnection.objects.first()
    db_form = DatabaseConnectionForm(
        request.POST or None,
        instance=db_profile,
        initial=_db_form_initial(db_profile),
    )
    sync_cfg = get_or_create_sync_config()
    sync_queue = SyncEvent.objects.aggregate(
        pending=models.Count("id", filter=models.Q(status=SyncEventStatus.PENDING)),
        failed=models.Count("id", filter=models.Q(status=SyncEventStatus.FAILED)),
        synced=models.Count("id", filter=models.Q(status=SyncEventStatus.SYNCED)),
        dead_letter=models.Count("id", filter=models.Q(is_dead_letter=True)),
    )
    sync_inbound_unprocessed = SyncInboundEvent.objects.filter(is_processed=False).count()

    def _extract_outbox_filters(data) -> dict:
        return {
            "status": (data.get("status") or "").strip(),
            "channel": (data.get("channel") or "").strip(),
            "event": (data.get("event") or "").strip(),
            "q": (data.get("q") or "").strip(),
            "unread": (data.get("unread") or "") == "1",
        }

    def _apply_outbox_filters(qs, filters: dict):
        status = filters.get("status") or ""
        channel = filters.get("channel") or ""
        event = filters.get("event") or ""
        q = filters.get("q") or ""
        unread = filters.get("unread") is True

        if status:
            qs = qs.filter(status=status)
        if channel:
            qs = qs.filter(channel=channel)
        if event:
            qs = qs.filter(event_key__icontains=event)
        if q:
            qs = qs.filter(
                models.Q(content__icontains=q)
                | models.Q(to_phone__icontains=q)
                | models.Q(to_email__icontains=q)
                | models.Q(event_key__icontains=q)
            )
        if unread:
            qs = qs.filter(is_read=False)
        return qs

    notification_setting = None
    outbox_filters = _extract_outbox_filters(request.GET)
    outbox_page = None
    if prop:
        notification_setting, created_setting = NotificationSetting.objects.get_or_create(property_profile=prop)
        outbox_qs = OutboxMessage.objects.filter(property_profile=prop).order_by("-created_at")
        if callable(_apply_outbox_filters):
            outbox_qs = _apply_outbox_filters(outbox_qs, outbox_filters)
        paginator = Paginator(outbox_qs, 20)
        outbox_page = paginator.get_page(request.GET.get("page") or 1)

    if prop:
        all_names = set()
        for mode_key, tiers in tier_presets.items():
            for tier_name in tier_names:
                all_names.update(tiers.get(tier_name, []))
        seed_amenities = not amenities.exists() and not UnitType.objects.filter(property_profile=prop).exists()
        for name in sorted(all_names) if seed_amenities else []:
            Amenity.objects.get_or_create(
                property_profile=prop,
                name_en=name,
                defaults={"name_ar": "", "is_active": True},
            )
        amenities = Amenity.objects.filter(property_profile=prop).order_by("name_en")

        for bt in [BusinessType.HOTEL, BusinessType.APARTMENTS]:
            for tier_name in tier_names:
                try:
                    UnitType.objects.get_or_create(
                        property_profile=prop,
                        business_type=bt,
                        name_en=tier_name,
                        defaults={"name_ar": "", "base_rate": Decimal("0.000"), "is_active": True},
                    )
                except IntegrityError:
                    # Pre-migration DB may still enforce unique (property, name_en)
                    pass

    if request.method == "POST":
        form_kind = (request.POST.get("form_kind") or "").strip()

        if form_kind == "property_create":
            if not can_manage_properties:
                messages.error(request, _("Only Owner/Admin can add properties."))
                return redirect("settings_page")

            name_en = (request.POST.get("create_name_en") or "").strip()
            if not name_en:
                messages.error(request, _("Property name (EN) is required."))
                return redirect("settings_page")

            selected_mode = (request.POST.get("create_business_type") or BusinessType.HOTEL).strip()
            if selected_mode not in {BusinessType.HOTEL, BusinessType.APARTMENTS}:
                selected_mode = BusinessType.HOTEL

            new_prop = PropertyProfile.objects.create(
                business_type=selected_mode,
                name_en=name_en,
                name_ar=(request.POST.get("create_name_ar") or "").strip(),
                currency=(request.POST.get("create_currency") or PropertyProfile.GCCCurrency.OMR).strip() or PropertyProfile.GCCCurrency.OMR,
                is_active=True,
            )
            request.session["active_property_id"] = new_prop.id
            messages.success(request, _("Property created and activated."))
            return redirect("settings_page")

        if form_kind == "amenity_add":
            amenity_form = AmenityForm(request.POST or None, prefix=amenity_form_prefix, property_obj=prop)
            valid_amenity = amenity_form.is_valid()
            if not prop:
                amenity_form.add_error(None, _("Create a property in the Property tab before adding amenities."))
            if valid_amenity and prop:
                obj = amenity_form.save(commit=False)
                obj.property_profile = prop
                obj.save()
                messages.success(request, "Amenity added.")
                return redirect(f"{reverse('settings_page')}?panel=amenities")

        elif form_kind == "backup_restore":
            action = (request.POST.get("action") or "").strip()
            if action == "backup":
                engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
                if "sqlite3" in engine:
                    db_path = settings.DATABASES.get("default", {}).get("NAME", "")
                    if not db_path or not os.path.exists(db_path):
                        messages.error(request, "SQLite database file not found.")
                        return redirect("settings_page")
                    with open(db_path, "rb") as f:
                        data = f.read()
                    resp = HttpResponse(data, content_type="application/octet-stream")
                    resp["Content-Disposition"] = "attachment; filename=backup.sqlite3"
                    return resp

                out = StringIO()
                call_command("dumpdata", stdout=out)
                resp = HttpResponse(out.getvalue(), content_type="application/json")
                resp["Content-Disposition"] = "attachment; filename=backup.json"
                return resp

            if action == "restore":
                upload = request.FILES.get("restore_file")
                if not upload:
                    messages.error(request, "Please choose a restore file.")
                    return redirect("settings_page")

                name = (upload.name or "").lower()
                engine = settings.DATABASES.get("default", {}).get("ENGINE", "")

                if name.endswith(".json"):
                    with NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                        tmp.write(upload.read())
                        tmp_path = tmp.name
                    try:
                        call_command("flush", interactive=False)
                        call_command("loaddata", tmp_path)
                        messages.success(request, "Restore completed from JSON backup.")
                    finally:
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
                    return redirect("settings_page")

                if "sqlite3" in engine and (name.endswith(".sqlite3") or name.endswith(".db")):
                    db_path = settings.DATABASES.get("default", {}).get("NAME", "")
                    if not db_path:
                        messages.error(request, "SQLite database path not configured.")
                        return redirect("settings_page")
                    try:
                        for conn in connections.all():
                            conn.close()
                        with open(db_path, "wb") as f:
                            f.write(upload.read())
                        messages.success(request, "SQLite database restored. Please refresh the app.")
                    except Exception as e:
                        messages.error(request, f"Restore failed: {e}")
                    return redirect("settings_page")

                messages.error(request, "Restore file type not supported for this database.")
                return redirect("settings_page")

            if action == "reset":
                confirm = (request.POST.get("confirm_reset") or "").strip().upper()
                if confirm != "DELETE":
                    messages.error(request, "Type DELETE to confirm reset.")
                    return redirect("settings_page")

                if not prop:
                    messages.error(request, "No active property selected.")
                    return redirect("settings_page")

                booking_type = BookingType.HOTEL if prop.business_type == BusinessType.HOTEL else BookingType.APARTMENT

                with transaction.atomic():
                    HousekeepingTask.objects.filter(
                        property_profile=prop,
                        unit__unit_type__business_type=prop.business_type,
                    ).delete()
                    MaintenanceRequest.objects.filter(
                        property_profile=prop,
                        unit__unit_type__business_type=prop.business_type,
                    ).delete()
                    MoveOutInspection.objects.filter(
                        property_profile=prop,
                        contract__unit__unit_type__business_type=prop.business_type,
                    ).delete()

                    ContractDocument.objects.filter(
                        property_profile=prop,
                        contract__unit__unit_type__business_type=prop.business_type,
                    ).delete()
                    Contract.objects.filter(
                        property_profile=prop,
                        unit__unit_type__business_type=prop.business_type,
                    ).delete()

                    Booking.objects.filter(
                        property_profile=prop,
                        booking_type=booking_type,
                    ).delete()
                    BookingGroup.objects.filter(
                        property_profile=prop,
                        booking_type=booking_type,
                    ).delete()

                    invoices = Invoice.objects.filter(property_profile=prop).filter(
                        models.Q(booking__booking_type=booking_type)
                        | models.Q(booking__isnull=True, guest__business_type=prop.business_type)
                    )
                    Payment.objects.filter(invoice__in=invoices).delete()
                    InvoiceLine.objects.filter(invoice__in=invoices).delete()
                    invoices.delete()

                    Guest.objects.filter(property_profile=prop, business_type=prop.business_type).delete()
                    Unit.objects.filter(property_profile=prop, unit_type__business_type=prop.business_type).delete()
                    UnitType.objects.filter(property_profile=prop, business_type=prop.business_type).delete()

                messages.success(request, "Reset completed for the active business mode.")
                return redirect("settings_page")

            if action == "save":
                messages.info(request, "Use Backup or Restore to run actions. Reset is separate.")
                return redirect("settings_page")

        elif form_kind == "db_settings":
            action = (request.POST.get("action") or "").strip()
            if not db_form.is_valid():
                messages.error(request, "Please correct the database settings.")
                return redirect("settings_page")

            password = (db_form.cleaned_data.get("password") or "").strip()
            if not password and db_profile:
                password = db_profile.get_password()

            if action in {"test", "migrate"} and not password:
                messages.error(request, "Password required to test or migrate.")
                return redirect("settings_page")

            if action in {"test", "migrate"}:
                db_config = _build_db_config(db_form.cleaned_data, password)
                ok, err = _test_db_connection(db_config)
                if not ok:
                    messages.error(request, f"Connection failed: {err}")
                    return redirect("settings_page")

            if action == "save":
                obj = db_form.save(commit=False)
                obj.engine = "django.db.backends.postgresql"
                obj.is_active = True
                if password:
                    obj.set_password(password)
                obj.save()
                messages.success(request, _("Database settings saved."))
                return redirect("settings_page")

            if action == "test":
                messages.success(request, _("Connection successful."))
                return redirect("settings_page")

            if action == "migrate":
                db_config = _build_db_config(db_form.cleaned_data, password)
                alias = "external_pg"
                tmp_path = None
                try:
                    connections.databases[alias] = db_config
                    call_command("migrate", database=alias, interactive=False)
                    out = StringIO()
                    call_command("dumpdata", stdout=out)
                    data = out.getvalue()
                    if not data.strip():
                        messages.error(request, "No data to migrate.")
                        return redirect("settings_page")
                    with NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                        tmp.write(data.encode("utf-8"))
                        tmp_path = tmp.name
                    call_command("loaddata", tmp_path, database=alias)
                    obj = db_form.save(commit=False)
                    obj.engine = "django.db.backends.postgresql"
                    obj.is_active = True
                    if password:
                        obj.set_password(password)
                    obj.save()
                    messages.success(request, _("Migration completed. Restart the app to switch databases."))
                except Exception as e:
                    messages.error(request, f"Migration failed: {e}")
                finally:
                    if tmp_path:
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
                    try:
                        conn = connections[alias]
                        conn.close()
                    except Exception:
                        pass
                    connections.databases.pop(alias, None)
                return redirect("settings_page")

            messages.error(request, "Unknown database action.")
            return redirect("settings_page")

        elif form_kind == "sync_settings":
            def _as_bool(name: str) -> bool:
                return request.POST.get(name) in {"on", "1", "true", "True"}

            sync_cfg.enabled = _as_bool("enabled")
            sync_cfg.push_enabled = _as_bool("push_enabled")
            sync_cfg.pull_enabled = _as_bool("pull_enabled")
            mode = (request.POST.get("mode") or "auto").strip()
            if mode not in {"offline", "online", "auto"}:
                mode = "auto"
            sync_cfg.mode = mode
            sync_cfg.remote_base_url = (request.POST.get("remote_base_url") or "").strip()
            sync_cfg.api_token = (request.POST.get("api_token") or "").strip()
            sync_cfg.shared_secret = (request.POST.get("shared_secret") or "").strip()
            sync_cfg.node_id = (request.POST.get("node_id") or sync_cfg.node_id or "").strip()
            sync_cfg.conflict_policy = (request.POST.get("conflict_policy") or "last_write_wins").strip()
            try:
                sync_cfg.interval_seconds = max(5, min(int(request.POST.get("interval_seconds") or 30), 3600))
            except Exception:
                sync_cfg.interval_seconds = 30
            try:
                sync_cfg.max_retry_attempts = max(1, min(int(request.POST.get("max_retry_attempts") or 8), 100))
            except Exception:
                sync_cfg.max_retry_attempts = 8
            sync_cfg.save()
            messages.success(request, _("Sync settings saved."))
            return redirect(f"{reverse('settings_page')}?panel=sync")

        elif form_kind == "sync_push_now":
            summary = push_pending_events(limit=200)
            if summary.get("failed"):
                messages.warning(request, _("Sync push completed with failures: %(detail)s") % {"detail": summary.get("detail", "")})
            else:
                messages.success(request, _("Sync push completed: %(synced)s events synced.") % {"synced": summary.get("synced", 0)})
            return redirect(f"{reverse('settings_page')}?panel=sync")

        elif form_kind == "sync_pull_now":
            summary = pull_remote_events(limit=200)
            if summary.get("failed"):
                messages.warning(request, _("Sync pull completed with issues: %(detail)s") % {"detail": summary.get("detail", "")})
            else:
                messages.success(request, _("Sync pull completed: %(applied)s events applied.") % {"applied": summary.get("applied", 0)})
            return redirect(f"{reverse('settings_page')}?panel=sync")

        elif form_kind == "sync_retry_now":
            retried_failed = reset_failed_events_for_retry(limit=1000)
            retried_dead = retry_dead_letters(limit=300)
            messages.success(
                request,
                _("Requeued %(failed)s failed and %(dead)s dead-letter events.")
                % {"failed": retried_failed, "dead": retried_dead},
            )
            return redirect(f"{reverse('settings_page')}?panel=sync")

        elif form_kind == "notifications_save":
            if not prop:
                messages.error(request, "No active property selected.")
                return redirect("settings_page")

            notification_setting, created_setting = NotificationSetting.objects.get_or_create(property_profile=prop)
            enable_whatsapp = request.POST.get("enable_whatsapp") == "on"
            default_channel = (request.POST.get("default_channel") or Channel.WHATSAPP).strip()
            valid_channels = {choice[0] for choice in Channel.choices}
            if default_channel not in valid_channels:
                default_channel = Channel.WHATSAPP
            notification_setting.enable_whatsapp = enable_whatsapp
            notification_setting.default_channel = default_channel
            notification_setting.notes = (request.POST.get("notes") or "").strip()
            notification_setting.save()
            messages.success(request, _("Notification settings saved."))
            return redirect("settings_page")

        elif form_kind == "notifications_mark_read":
            if not prop:
                messages.error(request, "No active property selected.")
                return redirect("settings_page")

            action = (request.POST.get("action") or "").strip()
            base_qs = OutboxMessage.objects.filter(property_profile=prop)

            if action == "mark_selected":
                raw_ids = request.POST.getlist("message_ids")
                msg_ids = [int(i) for i in raw_ids if i.isdigit()]
                if msg_ids:
                    base_qs.filter(id__in=msg_ids).update(is_read=True)
                    messages.success(request, _("Selected notifications marked as read."))
                else:
                    messages.info(request, _("Select at least one notification."))
            elif action == "mark_all":
                filters = _extract_outbox_filters(request.POST)
                filtered_qs = _apply_outbox_filters(base_qs, filters) if callable(_apply_outbox_filters) else base_qs
                updated = filtered_qs.update(is_read=True)
                if updated:
                    messages.success(request, _("All filtered notifications marked as read."))
                else:
                    messages.info(request, _("No notifications to mark as read."))
            else:
                messages.error(request, _("Unknown notification action."))

            next_url = (request.POST.get("next") or "").strip()
            return redirect(next_url or "settings_page")

        elif form_kind == "amenity_update":
            amenity_id = (request.POST.get("amenity_id") or "").strip()
            if not amenity_id.isdecimal():
                return HttpResponse(status=400)
            obj = get_object_or_404(Amenity, id=amenity_id, property_profile=prop)
            edit_form = AmenityForm(request.POST or None, instance=obj)
            if edit_form.is_valid():
                edit_form.save()
                messages.success(request, _("Amenity updated."))
                return redirect(f"{reverse('settings_page')}?panel=amenities")
            for errors in edit_form.errors.values():
                for error in errors:
                    messages.error(request, error)
            return redirect(f"{reverse('settings_page')}?panel=amenities")

        elif form_kind == "amenity_delete":
            amenity_id = (request.POST.get("amenity_id") or "").strip()
            if not amenity_id.isdecimal():
                return HttpResponse(status=400)
            obj = get_object_or_404(Amenity, id=amenity_id, property_profile=prop)
            obj.delete()
            messages.success(request, _("Amenity deleted."))
            return redirect(f"{reverse('settings_page')}?panel=amenities")

        elif form_kind in {"tier_amenity_add", "tier_amenity_remove"}:
            tier_name = (request.POST.get("tier_name") or "").strip()
            mode_key = (request.POST.get("mode_key") or "").strip()
            amenity_id = (request.POST.get("amenity_id") or "").strip()
            if not prop or tier_name not in tier_names or mode_key != prop.business_type or not amenity_id.isdecimal():
                return HttpResponse(status=400)
            unit_type = get_object_or_404(
                UnitType, property_profile=prop, business_type=mode_key, name_en=tier_name,
            )
            amenity = get_object_or_404(Amenity, property_profile=prop, pk=amenity_id)
            if form_kind == "tier_amenity_add":
                if not amenity.is_active:
                    return HttpResponse(status=400)
                unit_type.amenities.add(amenity)
                messages.success(request, _("Amenity added to tier."))
            else:
                unit_type.amenities.remove(amenity)
                messages.success(request, _("Amenity removed from tier."))
            return redirect(f"{reverse('settings_page')}?panel=amenities&tier={tier_name.lower()}")

        elif form_kind == "tier_amenities":
            tier_name = (request.POST.get("tier_name") or "").strip()
            mode_key = (request.POST.get("mode_key") or "").strip()
            amenity_ids = request.POST.getlist("amenity_ids")

            if not prop or tier_name not in tier_names or mode_key != prop.business_type:
                return HttpResponse(status=400)
            if tier_name in tier_names and mode_key in {"hotel", "apartments"}:
                business_type = BusinessType.HOTEL if mode_key == "hotel" else BusinessType.APARTMENTS
                unit_type = UnitType.objects.filter(
                    property_profile=prop,
                    business_type=business_type,
                    name_en=tier_name,
                ).first()
                if unit_type:
                    allowed_ids = set(Amenity.objects.filter(property_profile=prop, is_active=True).values_list("id", flat=True))
                    selected_ids = [int(i) for i in amenity_ids if i.isdigit() and int(i) in allowed_ids]
                    unit_type.amenities.set(selected_ids)
                    messages.success(request, _("%s amenities updated") % tier_name)
                    return redirect(f"{reverse('settings_page')}?panel=amenities&tier={tier_name.lower()}")

        elif form_kind == "business_type_switch":
            selected_mode = (request.POST.get("business_type") or "").strip()
            valid_modes = {BusinessType.HOTEL, BusinessType.APARTMENTS}
            if selected_mode in valid_modes:
                if prop is None:
                    # First-run desktop DB may have no property row yet; create one so mode can persist.
                    prop = PropertyProfile.objects.create(
                        business_type=selected_mode,
                        name_en="StayLux",
                    )
                elif prop.business_type != selected_mode:
                    prop.business_type = selected_mode
                    prop.save(update_fields=["business_type", "updated_at"])
                request.session["active_property_id"] = prop.id
            return redirect("settings_page")

        elif form_kind in {"", "settings_save"} and form.is_valid():
            obj = form.save()
            request.session["active_property_id"] = obj.id
            messages.success(request, _("Settings saved."))
            return redirect("settings_page")

        elif form_kind == "reset_data":
            confirm = (request.POST.get("confirm_reset") or "").strip().upper()
            if confirm != "DELETE":
                messages.error(request, "Type DELETE to confirm reset.")
                return redirect("settings_page")

            if not prop:
                messages.error(request, "No active property selected.")
                return redirect("settings_page")

            booking_type = BookingType.HOTEL if prop.business_type == BusinessType.HOTEL else BookingType.APARTMENT

            with transaction.atomic():
                HousekeepingTask.objects.filter(
                    property_profile=prop,
                    unit__unit_type__business_type=prop.business_type,
                ).delete()
                MaintenanceRequest.objects.filter(
                    property_profile=prop,
                    unit__unit_type__business_type=prop.business_type,
                ).delete()
                MoveOutInspection.objects.filter(
                    property_profile=prop,
                    contract__unit__unit_type__business_type=prop.business_type,
                ).delete()

                ContractDocument.objects.filter(
                    property_profile=prop,
                    contract__unit__unit_type__business_type=prop.business_type,
                ).delete()
                Contract.objects.filter(
                    property_profile=prop,
                    unit__unit_type__business_type=prop.business_type,
                ).delete()

                Booking.objects.filter(
                    property_profile=prop,
                    booking_type=booking_type,
                ).delete()
                BookingGroup.objects.filter(
                    property_profile=prop,
                    booking_type=booking_type,
                ).delete()

                invoices = Invoice.objects.filter(property_profile=prop).filter(
                    models.Q(booking__booking_type=booking_type)
                    | models.Q(booking__isnull=True, guest__business_type=prop.business_type)
                )
                Payment.objects.filter(invoice__in=invoices).delete()
                InvoiceLine.objects.filter(invoice__in=invoices).delete()
                invoices.delete()

                Guest.objects.filter(property_profile=prop, business_type=prop.business_type).delete()
                Unit.objects.filter(property_profile=prop, unit_type__business_type=prop.business_type).delete()
                UnitType.objects.filter(property_profile=prop, business_type=prop.business_type).delete()

            messages.success(request, "Reset completed for the active business mode.")
            return redirect("settings_page")

    for amenity in amenities:
        if not amenity.name_ar:
            amenity.name_ar = amenity_translations_fallback.get(amenity.name_en, "")
    amenity_by_name = {a.name_en: a for a in amenities if a.is_active}
    tier_tabs = []
    for tier_name in tier_names:
        hotel_unit_type = None
        apartments_unit_type = None
        if prop:
            hotel_unit_type = UnitType.objects.filter(
                property_profile=prop,
                business_type=BusinessType.HOTEL,
                name_en=tier_name,
            ).first()
            apartments_unit_type = UnitType.objects.filter(
                property_profile=prop,
                business_type=BusinessType.APARTMENTS,
                name_en=tier_name,
            ).first()

        hotel_selected = set(hotel_unit_type.amenities.values_list("id", flat=True)) if hotel_unit_type else set()
        apartments_selected = set(apartments_unit_type.amenities.values_list("id", flat=True)) if apartments_unit_type else set()

        lang = get_language() or ""
        # Fallback translations for common amenity names when `name_ar` is empty
        amenity_translations = AMENITY_AR_NAMES
        hotel_items = []
        for name in dict.fromkeys(tier_presets["hotel"].get(tier_name, []) + list(amenity_by_name)):
            amenity = amenity_by_name.get(name)
            if amenity:
                if lang.startswith("ar"):
                    display_name = amenity.name_ar or amenity_translations.get(amenity.name_en, amenity.name_en)
                else:
                    display_name = amenity.name_en
                hotel_items.append({"id": amenity.id, "name": display_name, "checked": amenity.id in hotel_selected})

        apartments_items = []
        for name in dict.fromkeys(tier_presets["apartments"].get(tier_name, []) + list(amenity_by_name)):
            amenity = amenity_by_name.get(name)
            if amenity:
                if lang.startswith("ar"):
                    display_name = amenity.name_ar or amenity_translations.get(amenity.name_en, amenity.name_en)
                else:
                    display_name = amenity.name_en
                apartments_items.append({"id": amenity.id, "name": display_name, "checked": amenity.id in apartments_selected})

        active_unit_type = apartments_unit_type if prop and prop.business_type == BusinessType.APARTMENTS else hotel_unit_type
        active_selected = apartments_selected if prop and prop.business_type == BusinessType.APARTMENTS else hotel_selected
        tier_tabs.append(
            {
                "name": tier_name,
                "display_name": (
                    {
                        "Standard": 'القياسي',
                        "Deluxe": 'ديلوكس',
                        "Premium": 'بريميوم',
                        "Luxury": 'فاخر',
                    }.get(tier_name, tier_name)
                    if lang.startswith("ar")
                    else tier_name
                ),
                "hotel_items": hotel_items,
                "apartments_items": apartments_items,
                "selected_amenities": list(active_unit_type.amenities.filter(property_profile=prop).order_by("name_en")) if active_unit_type else [],
                "available_amenities": [a for a in amenity_by_name.values() if a.id not in active_selected],
            }
        )

    return render(
        request,
        "core/settings.html",
        {
            "prop": prop,
            "all_properties": all_properties,
            "can_manage_properties": can_manage_properties,
            "form": form,
            "amenity_form": amenity_form,
            "active_panel": "amenities" if request.method == "POST" and request.POST.get("form_kind", "").startswith(("amenity_", "tier_amenit")) else request.GET.get("panel", "property"),
            "amenities": amenities,
            "tier_tabs": tier_tabs,
            "db_form": db_form,
            "db_profile": db_profile,
            "notification_setting": notification_setting,
            "notification_channels": Channel.choices,
            "notification_statuses": OutboxMessage._meta.get_field("status").choices,
            "outbox_page": outbox_page,
            "outbox_filters": outbox_filters,
            "sync_cfg": sync_cfg,
            "sync_queue": sync_queue,
            "sync_inbound_unprocessed": sync_inbound_unprocessed,
        },
    )


@login_required
def switch_active_property(request):
    if request.method not in {"GET", "POST"}:
        return redirect("dashboard")

    payload = request.POST if request.method == "POST" else request.GET
    next_url = (payload.get("next") or "").strip()
    if not next_url.startswith("/"):
        next_url = reverse("dashboard")

    if not _can_manage_properties(request.user):
        messages.error(request, _("Only Owner/Admin can switch properties."))
        return redirect(next_url)

    raw_id = (payload.get("property_id") or "").strip()
    try:
        prop_id = int(raw_id)
    except Exception:
        messages.error(request, _("Select a valid property."))
        return redirect(next_url)

    prop = PropertyProfile.objects.filter(id=prop_id, is_active=True).first()
    if not prop:
        messages.error(request, _("Selected property is not available."))
        return redirect(next_url)

    request.session["active_property_id"] = prop.id
    messages.success(request, _("Active property switched to %(name)s.") % {"name": prop.name_en})
    return redirect(next_url)


@login_required
def staff_list(request):
    if not _is_admin_manager(request.user):
        messages.error(request, "Staff management is available for Admin/Manager only.")
        return redirect("dashboard")

    prop = _get_active_property(request)
    qs = StaffProfile.objects.select_related("user").order_by("user__username")
    if prop:
        qs = qs.filter(property=prop)
    return render(request, "core/staff_list.html", {"prop": prop, "staff": qs[:500]})


@login_required
def staff_create(request):
    if not _is_admin_manager(request.user):
        messages.error(request, "Staff management is available for Admin/Manager only.")
        return redirect("dashboard")

    prop = _get_active_property(request)
    form = StaffCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        User = get_user_model()
        username = form.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            messages.error(request, _("Username already exists."))
            return render(request, "core/form_page.html", {"prop": prop, "title": _("Add Employee"), "form": form, "back_url": "staff_list"})

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data.get("first_name") or "",
                last_name=form.cleaned_data.get("last_name") or "",
                email=form.cleaned_data.get("email") or "",
                is_active=bool(form.cleaned_data.get("is_active")),
            )
            StaffProfile.objects.create(
                user=user,
                property=prop,
                role=form.cleaned_data["role"],
                is_active=bool(form.cleaned_data.get("is_active")),
            )

        messages.success(request, _("Employee created."))
        return redirect("staff_list")

    return render(request, "core/form_page.html", {"prop": prop, "title": _("Add Employee"), "form": form, "back_url": "staff_list"})


@login_required
def staff_edit(request, pk: int):
    if not _is_admin_manager(request.user):
        messages.error(request, "Staff management is available for Admin/Manager only.")
        return redirect("dashboard")

    prop = _get_active_property(request)
    profile = get_object_or_404(StaffProfile, pk=pk, property=prop)
    user = profile.user

    form = StaffEditForm(request.POST or None, initial={
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "role": profile.role,
        "is_active": profile.is_active,
    })
    if request.method == "POST" and form.is_valid():
        user.first_name = form.cleaned_data.get("first_name") or ""
        user.last_name = form.cleaned_data.get("last_name") or ""
        user.email = form.cleaned_data.get("email") or ""
        user.is_active = bool(form.cleaned_data.get("is_active"))
        if form.cleaned_data.get("reset_password"):
            user.set_password(form.cleaned_data["reset_password"])
        user.save()

        profile.role = form.cleaned_data["role"]
        profile.is_active = bool(form.cleaned_data.get("is_active"))
        profile.save()

        messages.success(request, _("Employee updated."))
        return redirect("staff_list")

    return render(request, "core/form_page.html", {"prop": prop, "title": _(f"Edit Employee #{profile.id}"), "form": form, "back_url": "staff_list"})


@login_required
def staff_delete(request, pk: int):
    if not _is_admin_manager(request.user):
        messages.error(request, "Staff management is available for Admin/Manager only.")
        return redirect("dashboard")

    prop = _get_active_property(request)
    profile = get_object_or_404(StaffProfile, pk=pk, property=prop)
    user = profile.user

    if request.method == "POST":
        profile.delete()
        user.is_active = False
        user.save()
        messages.success(request, _("Employee deactivated."))
        return redirect("staff_list")

    return render(request, "core/confirm_delete.html", {"prop": prop, "title": _("Deactivate Employee"), "object_label": user.username, "back_url": "staff_list"})


@login_required
def owners_list(request):
    if not _is_admin_manager(request.user):
        messages.error(request, _("Owner management is available for Admin/Manager only."))
        return redirect("dashboard")

    prop = _get_active_property(request)
    qs = OwnerProfile.objects.select_related("user").order_by("user__username")
    if prop:
        qs = qs.filter(property=prop)
    return render(request, "core/owners_list.html", {"prop": prop, "owners": qs[:500]})


@login_required
def owner_create(request):
    if not _is_admin_manager(request.user):
        messages.error(request, "Owner management is available for Admin/Manager only.")
        return redirect("dashboard")

    prop = _get_active_property(request)
    form = OwnerCreateForm(request.POST or None, property_obj=prop)
    if request.method == "POST" and form.is_valid():
        User = get_user_model()
        username = form.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            messages.error(request, _("Username already exists."))
            return render(request, "core/form_page.html", {"prop": prop, "title": _("Add Owner"), "form": form, "back_url": "owners_list"})

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data.get("first_name") or "",
                last_name=form.cleaned_data.get("last_name") or "",
                email=form.cleaned_data.get("email") or "",
                is_active=bool(form.cleaned_data.get("is_active")),
            )
            owner = OwnerProfile.objects.create(
                user=user,
                property=prop,
                is_active=bool(form.cleaned_data.get("is_active")),
            )
            owner.units.set(form.cleaned_data.get("units") or [])

        messages.success(request, _("Owner created."))
        return redirect("owners_list")

    return render(request, "core/form_page.html", {"prop": prop, "title": _("Add Owner"), "form": form, "back_url": "owners_list"})


@login_required
def owner_edit(request, pk: int):
    if not _is_admin_manager(request.user):
        messages.error(request, "Owner management is available for Admin/Manager only.")
        return redirect("dashboard")

    prop = _get_active_property(request)
    owner = get_object_or_404(OwnerProfile, pk=pk, property=prop)
    user = owner.user

    form = OwnerEditForm(
        request.POST or None,
        property_obj=prop,
        owner_instance=owner,
        initial={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_active": owner.is_active,
            "units": owner.units.all(),
        },
    )
    if request.method == "POST" and form.is_valid():
        user.first_name = form.cleaned_data.get("first_name") or ""
        user.last_name = form.cleaned_data.get("last_name") or ""
        user.email = form.cleaned_data.get("email") or ""
        user.is_active = bool(form.cleaned_data.get("is_active"))
        if form.cleaned_data.get("reset_password"):
            user.set_password(form.cleaned_data["reset_password"])
        user.save()

        owner.is_active = bool(form.cleaned_data.get("is_active"))
        owner.save()
        owner.units.set(form.cleaned_data.get("units") or [])

        messages.success(request, "Owner updated.")
        return redirect("owners_list")

    return render(request, "core/form_page.html", {"prop": prop, "title": f"Edit Owner #{owner.id}", "form": form, "back_url": "owners_list"})


@login_required
def owner_delete(request, pk: int):
    if not _is_admin_manager(request.user):
        messages.error(request, "Owner management is available for Admin/Manager only.")
        return redirect("dashboard")

    prop = _get_active_property(request)
    owner = get_object_or_404(OwnerProfile, pk=pk, property=prop)
    user = owner.user

    if request.method == "POST":
        owner.delete()
        user.is_active = False
        user.save()
        messages.success(request, "Owner deactivated.")
        return redirect("owners_list")

    return render(request, "core/confirm_delete.html", {"prop": prop, "title": "Deactivate Owner", "object_label": user.username, "back_url": "owners_list"})


@require_roles(ROLES_BILLING)
@login_required
def invoice_print_view(request, pk: int):
    prop = _get_active_property(request)
    invoice = get_object_or_404(Invoice.objects.prefetch_related("lines"), pk=pk, property_profile=prop)
    lang = (request.GET.get("lang") or getattr(request, "LANGUAGE_CODE", "en") or "en").lower()[:2]
    auto = (request.GET.get("auto") or "") == "1" or (request.GET.get("print") or "") == "1"
    download = (request.GET.get("download") or "") == "1"
    inline_pdf = (request.GET.get("inline") or "") == "1"
    user_agent = request.META.get("HTTP_USER_AGENT", "") or ""
    is_desktop_qt = "QtWebEngine" in user_agent or "QtWebEngineCore" in user_agent
    if download:
        is_ar = lang == "ar"
        filename = f"invoice_{invoice.invoice_no or invoice.id}.pdf"
        resp = HttpResponse(content_type="application/pdf")
        disposition = "inline" if inline_pdf else "attachment"
        resp["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        _build_invoice_pdf(resp, invoice=invoice, prop=invoice.property_profile, is_ar=is_ar)
        return resp
    tpl = "billing/invoice_print_ar.html" if lang == "ar" else "billing/invoice_print.html"
    return render(
        request,
        tpl,
        {
            "invoice": invoice,
            "property": invoice.property_profile,
            "auto": auto,
            "is_desktop_qt": is_desktop_qt,
        },
    )


@require_roles(ROLES_RECEPTION)
@login_required
def booking_agreement_print(request, pk: int):
    prop = _get_active_property(request)
    group = get_object_or_404(BookingGroup, pk=pk, property_profile=prop)
    guest = group.guest
    units = [b.unit for b in group.bookings.select_related("unit").all()]
    inv = group.invoices.order_by("-created_at").first()
    currency = inv.currency if inv else (prop.currency if prop else "OMR")
    total = inv.total if inv else Decimal("0.000")
    advance = inv.amount_paid if inv else Decimal("0.000")
    balance = inv.balance_due if inv else Decimal("0.000")

    lang = (request.GET.get("lang") or "en").lower()
    auto = (request.GET.get("auto") or "") == "1" or (request.GET.get("print") or "") == "1"
    download = (request.GET.get("download") or "") == "1"
    inline_pdf = (request.GET.get("inline") or "") == "1"
    user_agent = request.META.get("HTTP_USER_AGENT", "") or ""
    is_desktop_qt = "QtWebEngine" in user_agent or "QtWebEngineCore" in user_agent
    if download:
        is_ar = lang == "ar"
        filename = f"agreement_{group.id}.pdf"
        resp = HttpResponse(content_type="application/pdf")
        disposition = "inline" if inline_pdf else "attachment"
        resp["Content-Disposition"] = f'{disposition}; filename="{filename}"'
        _build_agreement_pdf(
            resp,
            group=group,
            guest=guest,
            units=units,
            currency=currency,
            total=total,
            advance=advance,
            balance=balance,
            prop=prop,
            is_ar=is_ar,
        )
        return resp
    tpl = "bookings/agreement_ar.html" if lang == "ar" else "bookings/agreement_en.html"
    return render(
        request,
        tpl,
        {
            "property": prop,
            "group": group,
            "guest": guest,
            "units": units,
            "currency": currency,
            "total": total,
            "advance": advance,
            "balance": balance,
            "auto": auto,
            "is_desktop_qt": is_desktop_qt,
        },
    )

