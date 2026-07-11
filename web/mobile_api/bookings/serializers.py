from rest_framework import serializers

from bookings.models import Booking
from inventory.models import Unit
from mobile_api.bookings.models import MobilePaymentRecord
from mobile_api.bookings.services import calculate_booking_quote


class BookingQuoteRequestSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    guest_count = serializers.IntegerField(min_value=1)
    coupon_code = serializers.CharField(required=False, allow_blank=True, default="")


class BookingCreateSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    guest_count = serializers.IntegerField(min_value=1)
    traveler_name = serializers.CharField(required=False, allow_blank=True, default="")
    traveler_email = serializers.EmailField(required=False, allow_blank=True, default="")
    traveler_phone = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    payment_method = serializers.CharField(required=False, allow_blank=True, default="")
    payment_provider = serializers.CharField(required=False, allow_blank=True, default="")
    payment_option = serializers.ChoiceField(
        choices=[("pay_now", "Pay now"), ("pay_at_property", "Pay at property")],
        required=False,
        default="pay_now",
    )
    idempotency_key = serializers.CharField(required=False, allow_blank=True, default=None)
    coupon_code = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_unit_id(self, value):
        if not Unit.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Selected unit was not found.")
        return value


class BookingPaymentIntentSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField(required=False)
    amount = serializers.DecimalField(max_digits=12, decimal_places=3)
    currency = serializers.CharField(max_length=10)
    payment_method = serializers.CharField(required=False, allow_blank=True, default="")
    provider = serializers.CharField(required=False, allow_blank=True, default="")
    idempotency_key = serializers.CharField(required=False, allow_blank=True, default=None)


class BookingSerializer(serializers.ModelSerializer):
    property_id = serializers.IntegerField(source="unit.property_profile.id", read_only=True)
    property_name = serializers.CharField(source="unit.property_profile.name_en", read_only=True)
    unit_code = serializers.CharField(source="unit.code", read_only=True)
    currency = serializers.CharField(source="unit.property_profile.currency", read_only=True)
    unit_id = serializers.IntegerField(source="unit.id", read_only=True)
    check_in = serializers.DateField(source="start_date", read_only=True)
    check_out = serializers.DateField(source="end_date", read_only=True)
    guest_count = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()

    def get_guest_count(self, obj):
        return int((obj.adults or 0) + (obj.children or 0))

    def get_total_amount(self, obj):
        locked_total = getattr(obj, "locked_total", None)
        if locked_total is not None and locked_total > 0:
            return locked_total
        try:
            estimated = obj.estimate_total()
            if estimated and estimated > 0:
                return estimated
        except Exception:
            pass

        # Backward compatibility for bookings created before total locking fix.
        request = self.context.get("request")
        customer = getattr(getattr(request, "user", None), "mobile_customer", None)
        if customer is not None:
            payment = (
                MobilePaymentRecord.objects.filter(
                    customer=customer,
                    booking_id=obj.id,
                )
                .order_by("-created_at")
                .first()
            )
            if payment and payment.amount and payment.amount > 0:
                return payment.amount
        return 0

    class Meta:
        model = Booking
        fields = [
            "id",
            "property_id",
            "property_name",
            "unit_id",
            "unit_code",
            "check_in",
            "check_out",
            "guest_count",
            "status",
            "currency",
            "total_amount",
            "created_at",
            "updated_at",
        ]


class BookingQuoteSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField()
    property_id = serializers.IntegerField()
    property_name = serializers.CharField()
    unit_code = serializers.CharField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    nights = serializers.IntegerField()
    guest_count = serializers.IntegerField()
    booking_type = serializers.CharField()
    rent_cycle = serializers.CharField()
    nightly_price = serializers.DecimalField(max_digits=12, decimal_places=3)
    monthly_price = serializers.DecimalField(max_digits=12, decimal_places=3)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=3)
    discount_amount = serializers.DecimalField(max_digits=12, decimal_places=3)
    discount_label = serializers.CharField(required=False, allow_blank=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True)
    taxes = serializers.DecimalField(max_digits=12, decimal_places=3)
    fees = serializers.DecimalField(max_digits=12, decimal_places=3)
    total = serializers.DecimalField(max_digits=12, decimal_places=3)
    currency = serializers.CharField()


class MobilePaymentRecordSerializer(serializers.ModelSerializer):
    verification_status = serializers.SerializerMethodField()
    risk_score = serializers.SerializerMethodField()
    requires_manual_review = serializers.SerializerMethodField()

    class Meta:
        model = MobilePaymentRecord
        fields = [
            "id",
            "booking_id",
            "provider",
            "provider_reference",
            "currency",
            "amount",
            "status",
            "payment_method",
            "client_secret",
            "notes",
            "verification_status",
            "risk_score",
            "requires_manual_review",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_verification_status(self, obj):
        check = getattr(obj, "security_check", None)
        return getattr(check, "verification_status", "pending")

    def get_risk_score(self, obj):
        check = getattr(obj, "security_check", None)
        return int(getattr(check, "risk_score", 0) or 0)

    def get_requires_manual_review(self, obj):
        check = getattr(obj, "security_check", None)
        return bool(getattr(check, "requires_manual_review", False))


def build_quote_response_data(quote):
    return {
        "unit_id": quote.unit.id,
        "property_id": quote.unit.property_profile.id,
        "property_name": quote.unit.property_profile.name_en,
        "unit_code": quote.unit.code,
        "check_in": quote.check_in,
        "check_out": quote.check_out,
        "nights": quote.nights,
        "guest_count": quote.guest_count,
        "booking_type": quote.booking_type,
        "rent_cycle": quote.rent_cycle,
        "nightly_price": quote.nightly_price,
        "monthly_price": quote.monthly_price,
        "subtotal": quote.subtotal,
        "discount_amount": quote.discount_amount,
        "discount_label": quote.discount_label,
        "coupon_code": quote.coupon_code,
        "taxes": quote.taxes,
        "fees": quote.fees,
        "total": quote.total,
        "currency": quote.currency,
    }
