from __future__ import annotations

import csv
from decimal import Decimal
from datetime import datetime

from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.db import models

from rest_framework import status as drf_status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from core.viewsets import PropertyScopedModelViewSet
from core.permissions import IsBillingStaff
from django.shortcuts import get_object_or_404

from bookings.models import Booking, BookingType
from notifications.services import queue_event_message

from .models import Invoice, InvoiceLine, Payment, InvoiceStatus, PaymentDirection
from .serializers import InvoiceSerializer, InvoiceLineSerializer, PaymentSerializer


class InvoiceViewSet(PropertyScopedModelViewSet):
    queryset = (
        Invoice.objects.select_related("property_profile", "guest", "booking")
        .prefetch_related("lines", "payments")
        .all()
    )
    serializer_class = InvoiceSerializer
    permission_classes = [IsBillingStaff]
    property_field_name = "property_profile"

    def get_queryset(self):
        qs = super().get_queryset()
        status_q = self.request.query_params.get("status")
        if status_q:
            qs = qs.filter(status=status_q)
        guest = self.request.query_params.get("guest")
        if guest:
            qs = qs.filter(guest_id=guest)
        booking = self.request.query_params.get("booking")
        if booking:
            qs = qs.filter(booking_id=booking)
        prop = self.get_property_profile()
        if prop:
            booking_type = BookingType.HOTEL if prop.business_type == "hotel" else BookingType.APARTMENT
            qs = qs.filter(
                models.Q(booking__booking_type=booking_type)
                | models.Q(booking__isnull=True, guest__business_type=prop.business_type)
            )
        return qs

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        inv = Invoice.objects.get(id=response.data["id"])
        inv.ensure_invoice_no()
        inv.recalc_and_save()

        if inv.status == InvoiceStatus.ISSUED:
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
        return response

    def update(self, request, *args, **kwargs):
        inv_before = self.get_object()
        prev_status = inv_before.status

        response = super().update(request, *args, **kwargs)
        inv = self.get_object()
        inv.ensure_invoice_no()
        inv.recalc_and_save()

        if prev_status != InvoiceStatus.ISSUED and inv.status == InvoiceStatus.ISSUED:
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
        return response

    @action(detail=False, methods=["post"])
    def generate_from_booking(self, request):
        """
        POST /api/invoices/generate_from_booking/
        Body:
          {
            "booking": 12,
            "issue": true,
            "tax_rate": "0.000"   (optional)
          }
        """
        booking_id = request.data.get("booking")
        if not booking_id:
            return Response({"detail": "booking is required"}, status=drf_status.HTTP_400_BAD_REQUEST)

        issue = bool(request.data.get("issue", True))
        tax_rate = Decimal(str(request.data.get("tax_rate", "0.000")))

        bookings = Booking.objects.select_related("property_profile", "guest", "unit")
        if not request.user.is_superuser:
            bookings = bookings.filter(property_profile_id=self._user_prop_id())
        booking = get_object_or_404(bookings, id=booking_id)

        inv = Invoice.objects.create(
            property_profile=booking.property_profile,
            booking=booking,
            guest=booking.guest,
            status=InvoiceStatus.ISSUED if issue else InvoiceStatus.DRAFT,
            issue_date=timezone.localdate() if issue else None,
            currency="OMR",
            notes=f"Auto-generated from booking #{booking.id}",
        )
        inv.ensure_invoice_no()

        # Line: accommodation nights * booking.rate
        nights = (booking.end_date - booking.start_date).days
        if nights < 1:
            nights = 1

        line = InvoiceLine.objects.create(
            invoice=inv,
            description=f"Accommodation {booking.unit.code} ({booking.start_date} → {booking.end_date})",
            quantity=Decimal(nights),
            unit_price=booking.rate,
            discount_amount=booking.discount,
            tax_rate=tax_rate,
        )
        line.recalc_tax()
        line.save(update_fields=["tax_amount"])

        inv.recalc_and_save()

        if inv.status == InvoiceStatus.ISSUED:
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

    @action(detail=True, methods=["post"])
    def add_line(self, request, pk=None):
        invoice = self.get_object()
        payload = request.data.copy()
        payload["invoice"] = invoice.id

        ser = InvoiceLineSerializer(data=payload)
        ser.is_valid(raise_exception=True)

        line: InvoiceLine = ser.save()
        line.recalc_tax()
        line.save(update_fields=["tax_amount"])

        invoice.recalc_and_save()
        return Response(InvoiceSerializer(invoice).data, status=drf_status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        """
        POST /api/invoices/{id}/void/
        Marks invoice VOID, voids all payments, recalculates.
        """
        inv = self.get_object()
        inv.status = InvoiceStatus.VOID
        inv.save(update_fields=["status", "updated_at"])

        inv.payments.all().update(is_void=True)
        inv.recalc_and_save()

        return Response(InvoiceSerializer(inv).data, status=drf_status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def refund(self, request, pk=None):
        """
        POST /api/invoices/{id}/refund/
        Body:
          { "amount": "10.000", "method": "cash", "reference": "...", "notes": "..." }
        Creates a refund payment (direction=out) and recalculates invoice.
        """
        inv = self.get_object()
        amount = request.data.get("amount")
        if not amount:
            return Response({"detail": "amount is required"}, status=drf_status.HTTP_400_BAD_REQUEST)

        pay = Payment.objects.create(
            invoice=inv,
            property_profile=inv.property_profile,
            method=request.data.get("method") or "cash",
            direction=PaymentDirection.OUT,
            amount=Decimal(str(amount)),
            reference=request.data.get("reference", ""),
            paid_at=timezone.now(),
            notes=request.data.get("notes", "Refund"),
        )
        inv.recalc_and_save()

        return Response(
            {"invoice": InvoiceSerializer(inv).data, "refund_payment": PaymentSerializer(pay).data},
            status=drf_status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def export_csv(self, request):
        """
        GET /api/invoices/export_csv/?property_profile=1&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
        """
        prop = request.query_params.get("property_profile")
        if not prop:
            return Response({"detail": "property_profile is required"}, status=drf_status.HTTP_400_BAD_REQUEST)

        sd = parse_date(request.query_params.get("start_date") or "")
        ed = parse_date(request.query_params.get("end_date") or "")

        qs = self.get_queryset().filter(property_profile_id=int(prop))
        if sd:
            qs = qs.filter(created_at__date__gte=sd)
        if ed:
            qs = qs.filter(created_at__date__lte=ed)

        filename = f"invoices_{prop}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(resp)
        writer.writerow(
            [
                "invoice_no",
                "status",
                "created_at",
                "guest",
                "total",
                "paid_net",
                "balance_due",
                "currency",
            ]
        )

        for inv in qs.select_related("guest").order_by("-created_at"):
            writer.writerow(
                [
                    inv.invoice_no,
                    inv.status,
                    inv.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    inv.guest.full_name,
                    str(inv.total),
                    str(inv.amount_paid),
                    str(inv.balance_due),
                    inv.currency,
                ]
            )

        return resp


class PaymentViewSet(PropertyScopedModelViewSet):
    queryset = Payment.objects.select_related("invoice", "property_profile").all()
    serializer_class = PaymentSerializer
    permission_classes = [IsBillingStaff]
    property_field_name = "property_profile"

    def get_queryset(self):
        qs = super().get_queryset()
        invoice = self.request.query_params.get("invoice")
        if invoice:
            qs = qs.filter(invoice_id=invoice)
        prop = self.get_property_profile()
        if prop:
            booking_type = BookingType.HOTEL if prop.business_type == "hotel" else BookingType.APARTMENT
            qs = qs.filter(
                models.Q(invoice__booking__booking_type=booking_type)
                | models.Q(invoice__booking__isnull=True, invoice__guest__business_type=prop.business_type)
            )
        return qs

    def perform_create(self, serializer):
        payment: Payment = super().perform_create(serializer)
        payment.invoice.recalc_and_save()

        inv = payment.invoice
        # only notify for money-in
        if payment.direction == PaymentDirection.IN:
            queue_event_message(
                property_profile=inv.property_profile,
                event_key="payment_received",
                to_phone=(inv.guest.whatsapp or inv.guest.phone),
                context={
                    "guest_name": inv.guest.full_name,
                    "invoice_no": inv.invoice_no or str(inv.id),
                    "paid_amount": str(payment.amount),
                    "total": str(inv.total),
                    "balance": str(inv.balance_due),
                },
            )

    def perform_update(self, serializer):
        payment: Payment = serializer.save()
        payment.invoice.recalc_and_save()
