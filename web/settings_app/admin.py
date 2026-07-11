from django.contrib import admin
from .models import PropertyProfile

@admin.register(PropertyProfile)
class PropertyProfileAdmin(admin.ModelAdmin):
    list_display = ("name_en", "business_type", "phone", "is_active", "updated_at")
    list_filter = ("business_type", "is_active")
    search_fields = ("name_en", "name_ar", "phone", "whatsapp", "email")
