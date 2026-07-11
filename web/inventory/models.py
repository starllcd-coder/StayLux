from django.db import models
from django.utils.encoding import force_str
from django.utils.translation import get_language, gettext_lazy as _
from core.models import TimeStampedModel
from settings_app.models import PropertyProfile, BusinessType


class UnitStatus(models.TextChoices):
    AVAILABLE = "available", _("Available")
    OCCUPIED = "occupied", _("Occupied")
    HOUSEKEEPING = "housekeeping", _("Housekeeping")
    MAINTENANCE = "maintenance", _("Maintenance")


def _localized_name(name_en: str, name_ar: str) -> str:
    lang = (get_language() or "").lower()
    if lang.startswith("ar"):
        if name_ar:
            return name_ar
        return force_str(_(name_en))
    return name_en


class Amenity(TimeStampedModel):
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="amenities")
    name_en = models.CharField(max_length=120)
    name_ar = models.CharField(max_length=120, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name_en"]
        unique_together = ("property_profile", "name_en")

    def __str__(self):
        return _localized_name(self.name_en, self.name_ar)


class UnitType(TimeStampedModel):
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="unit_types")
    business_type = models.CharField(max_length=20, choices=BusinessType.choices, default=BusinessType.HOTEL)
    name_en = models.CharField(max_length=120)
    name_ar = models.CharField(max_length=120, blank=True, default="")
    base_rate = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    is_active = models.BooleanField(default=True)
    amenities = models.ManyToManyField("Amenity", blank=True, related_name="unit_types")

    class Meta:
        ordering = ["name_en"]
        unique_together = ("property_profile", "business_type", "name_en")

    def __str__(self):
        return _localized_name(self.name_en, self.name_ar)


class Unit(TimeStampedModel):
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="units")
    unit_type = models.ForeignKey(UnitType, on_delete=models.PROTECT, related_name="units")

    class UnitCategory(models.TextChoices):
        # Hotel room types
        SINGLE = "single", _("Single")
        DOUBLE = "double", _("Double")
        TRIPLE = "triple", _("Triple")
        TWIN = "twin", _("Twin Room")
        KING = "king", _("King Room")
        QUEEN = "queen", _("Queen Room")
        CONNECTING = "connecting", _("Connecting / Adjoining Rooms")
        STUDIO = "studio", _("Studio")
        VILLA = "villa", _("Villa")

        # Apartment unit types
        STUDIO_APT = "studio_apartment", _("Studio Apartment")
        ONE_BHK = "1bhk", _("1-Room / BHK")
        TWO_BHK = "2bhk", _("2-Room / BHK")
        THREE_BHK = "3bhk", _("3-Room / BHK")
        FOUR_BHK = "4bhk", _("4-Room / BHK")
        FIVE_BHK = "5bhk", _("5-Room / BHK")
        DUPLEX = "duplex", _("Duplex / Triplex")
        PENTHOUSE = "penthouse", _("Penthouse")
        LOFT = "loft", _("Loft Apartment")

    class BedConfig(models.TextChoices):
        KING = "king", _("King")
        TWIN = "twin", _("Twin")
        QUEEN = "queen", _("Queen")

    code = models.CharField(max_length=50)  # room number or unit code
    floor = models.CharField(max_length=50, blank=True, default="")
    category = models.CharField(max_length=30, choices=UnitCategory.choices, blank=True, default="")
    bed_config = models.CharField(max_length=20, choices=BedConfig.choices, blank=True, default="")
    guest_capacity = models.PositiveIntegerField(default=1)

    daily_price = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    monthly_price = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    seasonal_price = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    amenities = models.ManyToManyField("Amenity", blank=True, related_name="units")
    status = models.CharField(max_length=20, choices=UnitStatus.choices, default=UnitStatus.AVAILABLE)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        unique_together = ("property_profile", "code")

    def __str__(self):
        return self.code