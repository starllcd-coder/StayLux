from __future__ import annotations

from datetime import date
from io import BytesIO

from django.http import JsonResponse, HttpResponse
from django.utils.dateparse import parse_date

from openpyxl import Workbook
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import A4

from core.security import get_user_property_profile_id
from bookings.models import Booking, BookingType
from settings_app.models import PropertyProfile


def _get_prop_id(request) -> int | None:
    if request.user.is_superuser and request.GET.get("property_profile"):
        return int(request.GET["property_profile"])
    return get_user_property_profile_id(request.user)


def _get_dates(request) -> tuple[date | None, date | None]:
    d1 = parse_date(request.GET.get("date_from", "") or "")
    d2 = parse_date(request.GET.get("date_to", "") or "")
    return d1, d2


def export_bookings_xlsx(request):
    prop_id = _get_prop_id(request)
    if not prop_id:
        return JsonResponse({"detail": "property_profile not resolved"}, status=400)

    prop = PropertyProfile.objects.filter(id=prop_id).first()
    if not prop:
        return JsonResponse({"detail": f"PropertyProfile {prop_id} not found"}, status=404)

    d1, d2 = _get_dates(request)
    if not d1 or not d2:
        return JsonResponse({"detail": "date_from and date_to are required (YYYY-MM-DD)"}, status=400)
    include_archived = str(request.GET.get("include_archived") or "").strip() in {"1", "true", "True", "yes", "on"}
    unit_id = request.GET.get("unit")

    booking_type = BookingType.HOTEL if prop.business_type == "hotel" else BookingType.APARTMENT

    qs = Booking.objects.select_related("unit", "guest").filter(
        property_profile_id=prop_id,
        booking_type=booking_type,
        unit__unit_type__business_type=prop.business_type,
        start_date__lt=d2,
        end_date__gt=d1,
    )
    if not include_archived:
        qs = qs.filter(is_archived=False)
    if unit_id:
        qs = qs.filter(unit_id=unit_id)
    qs = qs.order_by("-created_at")

    is_ar = (request.GET.get("lang") or "").lower() == "ar"

    wb = Workbook()
    ws = wb.active
    ws.title = "Bookings"
    headers = (
        ["المعرف", "الوحدة", "الضيف", "النوع", "الدورة", "الحالة", "البداية", "النهاية", "السعر", "الخصم", "الضمان", "مقفل", "الإجمالي"]
        if is_ar
        else ["ID", "Unit", "Guest", "Type", "Cycle", "Status", "Start", "End", "Rate", "Discount", "Deposit", "Locked", "Total"]
    )
    ws.append(headers)

    for b in qs:
        unit_code = getattr(b.unit, "code", str(b.unit_id))
        guest_name = getattr(b.guest, "full_name", str(b.guest_id))
        ws.append([
            b.id,
            unit_code,
            guest_name,
            b.booking_type,
            b.rent_cycle,
            b.status,
            str(b.start_date),
            str(b.end_date),
            str(b.rate),
            str(b.discount),
            str(b.deposit),
            "yes" if b.price_locked else "no",
            str(b.estimate_total()),
        ])

    ws.column_dimensions["A"].width = 10
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 28
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 16
    ws.column_dimensions["G"].width = 14
    ws.column_dimensions["H"].width = 14
    ws.column_dimensions["I"].width = 12
    ws.column_dimensions["J"].width = 12
    ws.column_dimensions["K"].width = 12
    ws.column_dimensions["L"].width = 12
    ws.column_dimensions["M"].width = 14

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    resp = HttpResponse(
        bio.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="bookings_{d1}_{d2}.xlsx"'
    return resp


def export_bookings_pdf(request):
    prop_id = _get_prop_id(request)
    if not prop_id:
        return JsonResponse({"detail": "property_profile not resolved"}, status=400)

    prop = PropertyProfile.objects.filter(id=prop_id).first()
    if not prop:
        return JsonResponse({"detail": f"PropertyProfile {prop_id} not found"}, status=404)

    d1, d2 = _get_dates(request)
    if not d1 or not d2:
        return JsonResponse({"detail": "date_from and date_to are required (YYYY-MM-DD)"}, status=400)
    include_archived = str(request.GET.get("include_archived") or "").strip() in {"1", "true", "True", "yes", "on"}
    unit_id = request.GET.get("unit")

    booking_type = BookingType.HOTEL if prop.business_type == "hotel" else BookingType.APARTMENT

    qs = Booking.objects.select_related("unit", "guest").filter(
        property_profile_id=prop_id,
        booking_type=booking_type,
        unit__unit_type__business_type=prop.business_type,
        start_date__lt=d2,
        end_date__gt=d1,
    )
    if not include_archived:
        qs = qs.filter(is_archived=False)
    if unit_id:
        qs = qs.filter(unit_id=unit_id)
    qs = qs.order_by("-created_at")[:300]

    bio = BytesIO()
    c = canvas.Canvas(bio, pagesize=A4)
    width, height = A4

    y = height - 40
    if getattr(prop, "logo", None) and hasattr(prop.logo, "path"):
        try:
            c.drawImage(ImageReader(prop.logo.path), 40, y - 26, width=24, height=24, preserveAspectRatio=True, mask="auto")
        except Exception:
            pass
    c.setFont("Helvetica-Bold", 12)
    c.drawString(70, y, prop.name_en or "StayLux")
    y -= 14
    c.setFont("Helvetica", 9)
    if prop.phone:
        c.drawString(70, y, f"Phone: {prop.phone}")
        y -= 12
    if prop.address_en:
        c.drawString(70, y, f"Address: {prop.address_en}"[:120])
        y -= 12
    if prop.cr_no:
        c.drawString(70, y, f"CR: {prop.cr_no}")
        y -= 12
    y -= 6

    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, f"Bookings Export ({d1} to {d2})")
    y -= 14
    c.setFont("Helvetica", 9)
    c.drawString(40, y, f"Records: {qs.count()}")
    y -= 16

    cols = [40, 76, 128, 216, 292, 352, 430, 500]
    headers = ["ID", "Unit", "Guest", "Status", "Start", "End", "Total"]
    c.setFont("Helvetica-Bold", 8)
    for i, h in enumerate(headers):
        c.drawString(cols[i], y, h)
    y -= 10
    c.line(40, y, 555, y)
    y -= 10
    c.setFont("Helvetica", 8)
    for b in qs:
        unit_code = getattr(b.unit, "code", str(b.unit_id))
        guest_name = getattr(b.guest, "full_name", str(b.guest_id))
        row = [
            f"#{b.id}",
            str(unit_code),
            str(guest_name)[:14],
            str(b.status),
            str(b.start_date),
            str(b.end_date),
            str(b.estimate_total()),
        ]
        for i, value in enumerate(row):
            c.drawString(cols[i], y, value[:14])
        y -= 10
        if y < 60:
            c.showPage()
            y = height - 40
            if getattr(prop, "logo", None) and hasattr(prop.logo, "path"):
                try:
                    c.drawImage(ImageReader(prop.logo.path), 40, y - 26, width=24, height=24, preserveAspectRatio=True, mask="auto")
                except Exception:
                    pass
            c.setFont("Helvetica-Bold", 12)
            c.drawString(70, y, prop.name_en or "StayLux")
            y -= 14
            c.setFont("Helvetica-Bold", 12)
            c.drawString(40, y, f"Bookings Export ({d1} to {d2})")
            y -= 14
            c.setFont("Helvetica-Bold", 8)
            for i, h in enumerate(headers):
                c.drawString(cols[i], y, h)
            y -= 10
            c.line(40, y, 555, y)
            y -= 10
            c.setFont("Helvetica", 8)

    c.showPage()
    c.save()
    bio.seek(0)

    resp = HttpResponse(bio.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="bookings_{d1}_{d2}.pdf"'
    return resp
