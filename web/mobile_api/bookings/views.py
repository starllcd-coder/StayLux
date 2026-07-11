from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q

from bookings.models import Booking
from inventory.models import Unit
from mobile_api.bookings.models import MobilePaymentRecord
from mobile_api.bookings.serializers import (
    BookingCreateSerializer,
    BookingPaymentIntentSerializer,
    BookingQuoteRequestSerializer,
    BookingQuoteSerializer,
    BookingSerializer,
    MobilePaymentRecordSerializer,
    build_quote_response_data,
)
from mobile_api.bookings.services import (
    calculate_booking_quote,
    cancel_customer_booking,
    create_mobile_booking,
    get_customer_booking_ids,
    create_payment_intent_placeholder,
    get_customer_guest_ids,
    run_payment_security_check,
)
from mobile_api.permissions import IsMobileCustomer


class BookingQuoteView(APIView):
    permission_classes = [IsMobileCustomer]

    def post(self, request, *args, **kwargs):
        serializer = BookingQuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        unit = Unit.objects.filter(id=serializer.validated_data["unit_id"], is_active=True).first()
        if not unit:
            raise NotFound("Selected unit was not found.")

        quote = calculate_booking_quote(
            unit=unit,
            check_in=serializer.validated_data["check_in"],
            check_out=serializer.validated_data["check_out"],
            guest_count=serializer.validated_data["guest_count"],
            coupon_code=serializer.validated_data.get("coupon_code", ""),
        )

        response_serializer = BookingQuoteSerializer(build_quote_response_data(quote))
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class BookingCreateView(APIView):
    permission_classes = [IsMobileCustomer]

    def post(self, request, *args, **kwargs):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        unit = Unit.objects.filter(id=serializer.validated_data["unit_id"], is_active=True).first()
        if not unit:
            raise NotFound("Selected unit was not found.")

        try:
            payment_option = serializer.validated_data.get("payment_option", "pay_now")
            booking, quote = create_mobile_booking(
                customer=request.user.mobile_customer,
                unit=unit,
                check_in=serializer.validated_data["check_in"],
                check_out=serializer.validated_data["check_out"],
                guest_count=serializer.validated_data["guest_count"],
                traveler_name=serializer.validated_data.get("traveler_name", ""),
                traveler_email=serializer.validated_data.get("traveler_email", ""),
                traveler_phone=serializer.validated_data.get("traveler_phone", ""),
                notes=serializer.validated_data.get("notes", ""),
                idempotency_key=serializer.validated_data.get("idempotency_key"),
                coupon_code=serializer.validated_data.get("coupon_code", ""),
            )

            if payment_option == "pay_at_property":
                payment = create_payment_intent_placeholder(
                    customer=request.user.mobile_customer,
                    booking_id=booking.id,
                    amount=quote.total,
                    currency=quote.currency,
                    payment_method="pay_at_property",
                    provider="property_frontdesk",
                    idempotency_key=serializer.validated_data.get("idempotency_key"),
                )
            else:
                payment = create_payment_intent_placeholder(
                    customer=request.user.mobile_customer,
                    booking_id=booking.id,
                    amount=quote.total,
                    currency=quote.currency,
                    payment_method=serializer.validated_data.get("payment_method", ""),
                    provider=serializer.validated_data.get("payment_provider", ""),
                    idempotency_key=serializer.validated_data.get("idempotency_key"),
                )
        except ValidationError:
            raise
        except Exception as exc:
            raise ValidationError({"booking": f"Could not complete booking request. ({exc})"})

        return Response(
            {
                "message": "Booking created successfully.",
                "booking": BookingSerializer(booking).data,
                "quote": BookingQuoteSerializer(build_quote_response_data(quote)).data,
                "payment": MobilePaymentRecordSerializer(payment).data,
                "payment_option": payment_option,
            },
            status=status.HTTP_201_CREATED,
        )


class CustomerBookingListView(ListAPIView):
    permission_classes = [IsMobileCustomer]
    serializer_class = BookingSerializer

    def get_queryset(self):
        guest_ids = get_customer_guest_ids(self.request.user.mobile_customer)
        booking_ids = get_customer_booking_ids(self.request.user.mobile_customer)
        if not guest_ids and not booking_ids:
            return Booking.objects.none()
        filters = Q()
        if guest_ids:
            filters |= Q(guest_id__in=guest_ids)
        if booking_ids:
            filters |= Q(id__in=booking_ids)
        return Booking.objects.filter(filters).select_related(
            "unit",
            "unit__property_profile",
        ).distinct().order_by("-created_at")


class CustomerBookingDetailView(RetrieveAPIView):
    permission_classes = [IsMobileCustomer]
    serializer_class = BookingSerializer
    lookup_field = "id"

    def get_queryset(self):
        guest_ids = get_customer_guest_ids(self.request.user.mobile_customer)
        booking_ids = get_customer_booking_ids(self.request.user.mobile_customer)
        if not guest_ids and not booking_ids:
            return Booking.objects.none()
        filters = Q()
        if guest_ids:
            filters |= Q(guest_id__in=guest_ids)
        if booking_ids:
            filters |= Q(id__in=booking_ids)
        return Booking.objects.filter(filters).select_related(
            "unit",
            "unit__property_profile",
        ).distinct()


class CustomerBookingCancelView(APIView):
    permission_classes = [IsMobileCustomer]

    def post(self, request, id, *args, **kwargs):
        guest_ids = get_customer_guest_ids(request.user.mobile_customer)
        booking_ids = get_customer_booking_ids(request.user.mobile_customer)
        if not guest_ids and not booking_ids:
            raise NotFound("Booking not found.")
        filters = Q(id=id)
        access_filters = Q()
        if guest_ids:
            access_filters |= Q(guest_id__in=guest_ids)
        if booking_ids:
            access_filters |= Q(id__in=booking_ids)
        booking = Booking.objects.filter(filters & access_filters).first()
        if not booking:
            raise NotFound("Booking not found.")

        booking = cancel_customer_booking(booking=booking)
        return Response(
            {
                "message": "Booking cancelled successfully.",
                "booking": BookingSerializer(booking).data,
            },
            status=status.HTTP_200_OK,
        )


class PaymentIntentCreateView(APIView):
    permission_classes = [IsMobileCustomer]

    def post(self, request, *args, **kwargs):
        serializer = BookingPaymentIntentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking_id = serializer.validated_data.get("booking_id")
        if booking_id:
            guest_ids = get_customer_guest_ids(request.user.mobile_customer)
            booking_ids = get_customer_booking_ids(request.user.mobile_customer)
            if not guest_ids and not booking_ids:
                raise NotFound("Booking not found.")
            access_filters = Q()
            if guest_ids:
                access_filters |= Q(guest_id__in=guest_ids)
            if booking_ids:
                access_filters |= Q(id__in=booking_ids)
            booking = Booking.objects.filter(Q(id=booking_id) & access_filters).first()
            if not booking:
                raise NotFound("Booking not found.")

        payment = create_payment_intent_placeholder(
            customer=request.user.mobile_customer,
            booking_id=booking_id,
            amount=serializer.validated_data["amount"],
            currency=serializer.validated_data["currency"],
            payment_method=serializer.validated_data.get("payment_method", ""),
            provider=serializer.validated_data.get("provider", ""),
            idempotency_key=serializer.validated_data.get("idempotency_key"),
        )

        return Response(
            {
                "message": "Payment intent created.",
                "payment": MobilePaymentRecordSerializer(payment).data,
                "provider_integration": "pending_gateway_integration",
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentRecordListView(ListAPIView):
    permission_classes = [IsMobileCustomer]
    serializer_class = MobilePaymentRecordSerializer

    def get_queryset(self):
        return MobilePaymentRecord.objects.filter(
            customer=self.request.user.mobile_customer
        ).order_by("-created_at")


class PaymentVerifyView(APIView):
    permission_classes = [IsMobileCustomer]

    def post(self, request, id, *args, **kwargs):
        payment = MobilePaymentRecord.objects.filter(
            id=id,
            customer=request.user.mobile_customer,
        ).first()
        if not payment:
            raise NotFound("Payment record not found.")

        check = run_payment_security_check(
            payment=payment,
            otp_code=(request.data.get("otp_code") or "").strip(),
            billing_country=(request.data.get("billing_country") or "").strip(),
        )

        return Response(
            {
                "message": "Payment verification completed.",
                "payment": MobilePaymentRecordSerializer(payment).data,
                "security": {
                    "verification_status": check.verification_status,
                    "risk_score": check.risk_score,
                    "requires_manual_review": check.requires_manual_review,
                    "fraud_flags": check.fraud_flags,
                },
            },
            status=status.HTTP_200_OK,
        )


class PaymentSecurityConfigView(APIView):
    permission_classes = [IsMobileCustomer]

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "pci_mode": "scaffolded",
                "tokenization": True,
                "3ds_supported": True,
                "fraud_scoring": "enabled",
                "notes": "Production PCI/fraud provider certification required for go-live.",
            },
            status=status.HTTP_200_OK,
        )
