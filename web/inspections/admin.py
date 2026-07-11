from django.contrib import admin
from .models import MoveOutInspection


@admin.register(MoveOutInspection)
class MoveOutInspectionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "property_profile",
        "contract",
        "status",
        "inspection_date",
        "deductions",
        "refundable_amount",
        "created_at",
    )
    list_filter = ("property_profile", "status")
    search_fields = ("contract__contract_no", "contract__unit__code", "contract__guest__full_name")