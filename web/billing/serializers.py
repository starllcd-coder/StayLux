from rest_framework import serializers
from .models import Invoice, InvoiceLine, Payment


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


class PaymentSerializer(serializers.ModelSerializer):
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


class InvoiceSerializer(serializers.ModelSerializer):
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