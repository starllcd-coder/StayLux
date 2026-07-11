from django.db import models

from core.models import TimeStampedModel
from mobile_api.auth.models import MobileCustomer


class MembershipPlan(TimeStampedModel):
    name = models.CharField(max_length=120)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    annual_fee = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    benefits = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["monthly_fee", "name"]


class CustomerMembership(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    customer = models.ForeignKey(MobileCustomer, on_delete=models.CASCADE, related_name="memberships")
    plan = models.ForeignKey(MembershipPlan, on_delete=models.PROTECT, related_name="memberships")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    started_at = models.DateTimeField(null=True, blank=True)
    renews_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ReferralInvite(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REWARDED = "rewarded", "Rewarded"

    referrer = models.ForeignKey(MobileCustomer, on_delete=models.CASCADE, related_name="referral_invites")
    referred_email = models.EmailField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reward_points = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
