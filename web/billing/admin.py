from django.contrib import admin
from .models import Invoice, InvoiceLine, Payment


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "invoice_no",
        "property_profile",
        "guest",
        "status",
        "total",
        "amount_paid",
        "balance_due",
        "created_at",
    )
    list_filter = ("property_profile", "status")
    search_fields = ("invoice_no", "guest__full_name", "guest__phone")
    inlines = [InvoiceLineInline, PaymentInline]


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = ("id", "invoice", "description", "quantity", "unit_price", "discount_amount", "tax_rate", "tax_amount")
    search_fields = ("description",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "invoice", "property_profile", "method", "direction", "amount", "is_void", "created_at")
    list_filter = ("property_profile", "method", "direction", "is_void")
    search_fields = ("reference", "invoice__invoice_no")