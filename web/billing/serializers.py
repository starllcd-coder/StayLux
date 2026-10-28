from rest_framework import serializers
from .models import Invoice, InvoiceLine, Payment
from core.security import get_user_role


class PropertyBillingValidation:
    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        if not request or request.user.is_superuser:
            return attrs
        staff = getattr(request.user, "staff_profile", None)
        if not staff or not staff.is_active:
            raise serializers.ValidationError("An active billing staff profile is required.")
        for field in ["property_profile", "guest", "booking", "invoice"]:
            obj = attrs.get(field)
            if obj is None:
                continue
            prop_id = obj.pk if field == "property_profile" else obj.property_profile_id
            if prop_id != staff.property_id:
                raise serializers.ValidationError({field: "Select a record from your assigned property."})
        if get_user_role(request.user) == "accounts":
            if attrs.get("status") == "void" or attrs.get("is_void") is True:
                raise serializers.ValidationError("Voiding financial records requires Owner/Admin or Manager approval.")
        return attrs


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            "id",
            "invoice",
            "description",
            "quantity",
            "unit_price",
            "discount_amount",
            "tax_rate",
            "tax_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("tax_amount", "created_at", "updated_at")


class PaymentSerializer(PropertyBillingValidation, serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "invoice",
            "property_profile",
            "method",
            "direction",
            "amount",
            "reference",
            "paid_at",
            "is_void",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("created_at", "updated_at")


class InvoiceSerializer(PropertyBillingValidation, serializers.ModelSerializer):
    lines = InvoiceLineSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "property_profile",
            "booking",
            "guest",
            "invoice_no",
            "status",
            "issue_date",
            "due_date",
            "currency",
            "subtotal",
            "discount_total",
            "tax_total",
            "total",
            "amount_paid",
            "balance_due",
            "notes",
            "lines",
            "payments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = (
            "invoice_no",
            "subtotal",
            "discount_total",
            "tax_total",
            "total",
            "amount_paid",
            "balance_due",
            "created_at",
            "updated_at",
        )
