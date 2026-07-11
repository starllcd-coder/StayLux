from django.contrib import admin
from .models import Contract, ContractDocument


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "contract_no",
        "property_profile",
        "unit",
        "guest",
        "status",
        "monthly_rent",
        "billing_day",
        "deposit_status",
        "deposit_invoice",
        "end_date",
        "move_out_date",
        "created_at",
    )
    list_filter = ("property_profile", "status", "deposit_status")
    search_fields = ("contract_no", "unit__code", "guest__full_name", "guest__phone")


@admin.register(ContractDocument)
class ContractDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "property_profile", "contract", "doc_type", "title", "created_at")
    list_filter = ("property_profile", "doc_type")
    search_fields = ("title", "contract__contract_no", "contract__unit__code", "contract__guest__full_name")