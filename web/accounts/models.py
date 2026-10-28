from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db import models
from core.models import TimeStampedModel
from settings_app.models import PropertyProfile
from inventory.models import Unit

class StaffRole(models.TextChoices):
    OWNER_ADMIN = "owner_admin", _("Owner/Admin")
    MANAGER = "manager", _("Manager")
    ACCOUNTS = "accounts", _("Accounts")
    RECEPTION = "reception", _("Reception/Front Desk")
    HOUSEKEEPING = "housekeeping", _("Housekeeping")
    MAINTENANCE = "maintenance", _("Maintenance")

class StaffProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="staff_profile")
    property = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="staff")
    role = models.CharField(max_length=30, choices=StaffRole.choices, default=StaffRole.RECEPTION)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class OwnerProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="owner_profile")
    property = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="owners")
    units = models.ManyToManyField(Unit, blank=True, related_name="owners")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} (Owner)"
