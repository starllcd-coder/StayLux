from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string

from core.models import TimeStampedModel


class MobileCustomer(TimeStampedModel):
    class PreferredLanguage(models.TextChoices):
        EN = "en", "English"
        AR = "ar", "Arabic"

    class AuthProvider(models.TextChoices):
        EMAIL = "email", "Email"
        GOOGLE = "google", "Google"
        APPLE = "apple", "Apple"
        PHONE = "phone", "Phone"

    class LoyaltyTier(models.TextChoices):
        BRONZE = "bronze", "Bronze"
        SILVER = "silver", "Silver"
        GOLD = "gold", "Gold"
        PLATINUM = "platinum", "Platinum"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mobile_customer",
    )
    full_name = models.CharField(max_length=200)
    mobile = models.CharField(max_length=50, blank=True, default="")
    preferred_language = models.CharField(
        max_length=10,
        choices=PreferredLanguage.choices,
        default=PreferredLanguage.EN,
    )
    preferred_country = models.CharField(max_length=120, blank=True, default="")
    auth_provider = models.CharField(
        max_length=20,
        choices=AuthProvider.choices,
        default=AuthProvider.EMAIL,
    )
    external_subject = models.CharField(max_length=255, blank=True, default="")
    is_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    marketing_opt_in = models.BooleanField(default=False)
    email_notifications_enabled = models.BooleanField(default=True)
    push_notifications_enabled = models.BooleanField(default=True)
    sms_notifications_enabled = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(blank=True, null=True)
    loyalty_points = models.PositiveIntegerField(default=0)
    loyalty_tier = models.CharField(
        max_length=20,
        choices=LoyaltyTier.choices,
        default=LoyaltyTier.BRONZE,
    )
    referral_code = models.CharField(max_length=32, blank=True, default="", db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["preferred_country"]),
            models.Index(fields=["preferred_language"]),
            models.Index(fields=["auth_provider"]),
            models.Index(fields=["mobile"]),
            models.Index(fields=["referral_code"]),
            models.Index(fields=["loyalty_tier"]),
        ]

    def __str__(self):
        return self.full_name or self.user.get_username()

    @property
    def email(self) -> str:
        return self.user.email

    def mark_login(self) -> None:
        self.last_login_at = timezone.now()
        self.save(update_fields=["last_login_at", "updated_at"])

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self._generate_referral_code()
        super().save(*args, **kwargs)

    def _generate_referral_code(self) -> str:
        prefix = (self.full_name or "STAY").upper().replace(" ", "")[:5] or "STAY"
        for _ in range(6):
            code = f"{prefix}{get_random_string(6).upper()}"
            if not MobileCustomer.objects.filter(referral_code=code).exists():
                return code
        return get_random_string(10).upper()

    def add_loyalty_points(self, points: int) -> None:
        pts = max(int(points or 0), 0)
        if pts <= 0:
            return
        self.loyalty_points = int(self.loyalty_points or 0) + pts
        if self.loyalty_points >= 5000:
            self.loyalty_tier = self.LoyaltyTier.PLATINUM
        elif self.loyalty_points >= 2000:
            self.loyalty_tier = self.LoyaltyTier.GOLD
        elif self.loyalty_points >= 800:
            self.loyalty_tier = self.LoyaltyTier.SILVER
        else:
            self.loyalty_tier = self.LoyaltyTier.BRONZE
        self.save(update_fields=["loyalty_points", "loyalty_tier", "updated_at"])


class MobileVerificationCode(TimeStampedModel):
    class Purpose(models.TextChoices):
        EMAIL_VERIFY = "email_verify", "Email Verify"
        TWO_FACTOR = "two_factor", "Two Factor"

    customer = models.ForeignKey(MobileCustomer, on_delete=models.CASCADE, related_name="verification_codes")
    purpose = models.CharField(max_length=30, choices=Purpose.choices)
    channel = models.CharField(max_length=20, blank=True, default="email")
    target = models.CharField(max_length=255, blank=True, default="")
    code = models.CharField(max_length=10)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "purpose", "is_used"]),
            models.Index(fields=["expires_at"]),
        ]
