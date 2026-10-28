from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core import signing
from core.models import TimeStampedModel

class BusinessType(models.TextChoices):
    HOTEL = "hotel", _("Hotel")
    APARTMENTS = "apartments", _("Apartments")


class ChannelIntegration(models.Model):
    class Platform(models.TextChoices):
        AGODA = "agoda", "Agoda"
        BOOKING = "booking", "Booking.com"
        AIRBNB = "airbnb", "Airbnb"

    property_profile = models.ForeignKey("PropertyProfile", on_delete=models.CASCADE, related_name="channel_integrations")
    platform = models.CharField(max_length=20, choices=Platform.choices)
    external_property_id = models.CharField(max_length=120, blank=True)
    account_reference = models.CharField(max_length=120, blank=True)
    unit_mappings = models.JSONField(default=dict, blank=True)
    authentication_method = models.CharField(max_length=20, choices=[("api_token", "API token/key"), ("oauth", "OAuth client"), ("machine_account", "API machine account")], default="api_token")
    credentials_encrypted = models.TextField(blank=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    def get_credentials(self):
        import json
        from .channel_security import credential_cipher
        if not self.credentials_encrypted:
            return {}
        return json.loads(credential_cipher().decrypt(self.credentials_encrypted.encode()).decode())

    def set_credentials(self, values):
        import json
        from .channel_security import credential_cipher
        self.credentials_encrypted = credential_cipher().encrypt(json.dumps(values).encode()).decode() if values else ""

    class Meta:
        constraints = [models.UniqueConstraint(fields=["property_profile", "platform"], name="unique_property_channel")]

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
