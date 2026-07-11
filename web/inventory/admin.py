from django.contrib import admin
from .models import Amenity, UnitType, Unit


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ("name_en", "property_profile", "is_active", "created_at")
    list_filter = ("property_profile", "is_active")
    search_fields = ("name_en", "name_ar")


@admin.register(UnitType)
class UnitTypeAdmin(admin.ModelAdmin):
    list_display = ("name_en", "property_profile", "base_rate", "is_active", "created_at")
    list_filter = ("property_profile", "is_active")
    search_fields = ("name_en", "name_ar")


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("code", "property_profile", "unit_type", "status", "is_active", "created_at")
    list_filter = ("property_profile", "status", "is_active")
    search_fields = ("code", "floor")