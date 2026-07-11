from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core import signing
from core.models import TimeStampedModel

class BusinessType(models.TextChoices):
    HOTEL = "hotel", _("Hotel")
    APARTMENTS = "apartments", _("Apartments")

class PropertyProfile(TimeStampedModel):
    """One property (hotel/apartment building) profile & branding."""
    business_type = models.CharField(max_length=20, choices=BusinessType.choices, default=BusinessType.HOTEL)

    name_en = models.CharField(max_length=200)
    name_ar = models.CharField(max_length=200, blank=True, default="")

    logo = models.ImageField(upload_to="property/logo/", blank=True, null=True)

    property_number = models.CharField(max_length=50, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    country = models.CharField(max_length=120, blank=True, default="")

    phone = models.CharField(max_length=50, blank=True, default="")
    whatsapp = models.CharField(max_length=50, blank=True, default="")
    email = models.EmailField(blank=True, default="")

    address_en = models.TextField(blank=True, default="")
    address_ar = models.TextField(blank=True, default="")

    vat_no = models.CharField(max_length=50, blank=True, default="")
    cr_no = models.CharField(max_length=50, blank=True, default="")

    receipt_footer_en = models.TextField(blank=True, default="")
    receipt_footer_ar = models.TextField(blank=True, default="")

    class GCCCurrency(models.TextChoices):
        OMR = "OMR", _("Omani Rial (OMR)")
        AED = "AED", _("UAE Dirham (AED)")
        SAR = "SAR", _("Saudi Riyal (SAR)")
        KWD = "KWD", _("Kuwaiti Dinar (KWD)")
        BHD = "BHD", _("Bahraini Dinar (BHD)")
        QAR = "QAR", _("Qatari Riyal (QAR)")

    currency = models.CharField(max_length=10, choices=GCCCurrency.choices, default=GCCCurrency.OMR)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name_en


class DatabaseConnection(TimeStampedModel):
    name = models.CharField(max_length=120, default="Primary Database")
    engine = models.CharField(max_length=200, default="django.db.backends.postgresql")
    host = models.CharField(max_length=200)
    port = models.CharField(max_length=20, default="5432")
    db_name = models.CharField(max_length=200)
    username = models.CharField(max_length=200)
    password_enc = models.TextField(blank=True, default="")
    sslmode = models.CharField(max_length=20, default="require")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def set_password(self, raw: str) -> None:
        if raw:
            self.password_enc = signing.dumps(raw, salt="staylux.db")

    def get_password(self) -> str:
        if not self.password_enc:
            return ""
        try:
            return signing.loads(self.password_enc, salt="staylux.db")
        except Exception:
            return ""
