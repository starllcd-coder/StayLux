from django.db import models
from core.models import TimeStampedModel
from settings_app.models import PropertyProfile


class Channel(models.TextChoices):
    WHATSAPP = "whatsapp", "WhatsApp"
    SMS = "sms", "SMS"
    EMAIL = "email", "Email"


class StaffJobNotification(TimeStampedModel):
    recipient = models.ForeignKey("accounts.StaffProfile", on_delete=models.CASCADE, related_name="job_notifications")
    housekeeping_task = models.ForeignKey("housekeeping.HousekeepingTask", null=True, blank=True, on_delete=models.CASCADE)
    maintenance_request = models.ForeignKey("maintenance.MaintenanceRequest", null=True, blank=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at", "-id"]


class NotificationSetting(TimeStampedModel):
    property_profile = models.OneToOneField(PropertyProfile, on_delete=models.CASCADE, related_name="notification_setting")

    enable_whatsapp = models.BooleanField(default=False)
    default_channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.WHATSAPP)

    # later you can store provider config keys safely in env/secret manager
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"NotificationSetting({self.property_profile_id})"


class StaffPushDevice(TimeStampedModel):
    recipient = models.ForeignKey("accounts.StaffProfile", on_delete=models.CASCADE, related_name="push_devices")
    token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=10, choices=[("android", "Android"), ("ios", "iOS")])
    is_active = models.BooleanField(default=True)


class StaffPushDelivery(TimeStampedModel):
    notification = models.ForeignKey(StaffJobNotification, on_delete=models.CASCADE, related_name="push_deliveries")
    device = models.ForeignKey(StaffPushDevice, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    error_code = models.CharField(max_length=80, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["notification", "device"], name="unique_staff_push_delivery")]


class WhatsAppTemplate(TimeStampedModel):
    """
    Store a template *key* and a message body.
    Later, connect key -> Meta approved template name.
    """
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="wa_templates")

    key = models.CharField(max_length=80)  # e.g. invoice_issued, payment_received, booking_confirmed
    language = models.CharField(max_length=10, default="en")  # en/ar
    body = models.TextField()  # supports {placeholders}

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("property_profile", "key", "language")
        indexes = [models.Index(fields=["property_profile", "key", "language"])]

    def __str__(self):
        return f"{self.key} ({self.language})"


class OutboxStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class OutboxMessage(TimeStampedModel):
    property_profile = models.ForeignKey(PropertyProfile, on_delete=models.CASCADE, related_name="outbox_messages")

    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.WHATSAPP)
    to_phone = models.CharField(max_length=50, blank=True, default="")
    to_email = models.EmailField(blank=True, default="")

    event_key = models.CharField(max_length=80, blank=True, default="")
    language = models.CharField(max_length=10, default="en")

    content = models.TextField()
    status = models.CharField(max_length=20, choices=OutboxStatus.choices, default=OutboxStatus.PENDING)

    is_read = models.BooleanField(default=False)

    provider_message_id = models.CharField(max_length=120, blank=True, default="")
    error = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property_profile", "status"]),
            models.Index(fields=["property_profile", "event_key"]),
            models.Index(fields=["property_profile", "is_read"]),
        ]

    def __str__(self):
        return f"{self.channel} {self.status} -> {self.to_phone or self.to_email}"
