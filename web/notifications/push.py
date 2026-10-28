"""Optional Firebase sender. Disabled installations never import the SDK."""
import logging
from datetime import timedelta
from threading import Lock

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import StaffJobNotification, StaffPushDevice, StaffPushDelivery

logger = logging.getLogger(__name__)
_app_lock = Lock()


def send_firebase(token, notification):
    import firebase_admin
    from firebase_admin import credentials, messaging

    with _app_lock:
        try:
            app = firebase_admin.get_app("staylux-push")
        except ValueError:
            credential = credentials.Certificate(settings.FIREBASE_SERVICE_ACCOUNT_FILE) if settings.FIREBASE_SERVICE_ACCOUNT_FILE else credentials.ApplicationDefault()
            app = firebase_admin.initialize_app(credential, {"httpTimeout": 5}, name="staylux-push")
    return messaging.send(messaging.Message(
        token=token,
        notification=messaging.Notification(
            title=notification.title,
            # Keep guest and unit details off phone lock screens.
            body="A job has been assigned to you. Open StayLux to view it.",
        ),
        data={"notification_id": str(notification.pk), "type": "staff_job"},
        android=messaging.AndroidConfig(priority="high", ttl=timedelta(hours=24)),
        apns=messaging.APNSConfig(payload=messaging.APNSPayload(aps=messaging.Aps(sound="default"))),
    ), app=app)


def dispatch_notification(notification_id):
    if not settings.FIREBASE_PUSH_ENABLED:
        return
    notification = StaffJobNotification.objects.select_related(
        "recipient__user", "housekeeping_task", "maintenance_request",
    ).filter(pk=notification_id).first()
    if not notification or notification.is_read:
        return
    staff = notification.recipient
    job = notification.housekeeping_task or notification.maintenance_request
    if not job or job.assigned_to_id != staff.pk or job.property_profile_id != staff.property_id:
        return
    if not staff.is_active or not staff.user.is_active or job.status in {"done", "resolved", "cancelled"}:
        return
    role = "housekeeping" if notification.housekeeping_task_id else "maintenance"
    if staff.role not in {role, "manager", "owner_admin"}:
        return
    for device in StaffPushDevice.objects.filter(recipient=staff, is_active=True):
        delivery, _ = StaffPushDelivery.objects.get_or_create(notification=notification, device=device)
        with transaction.atomic():
            delivery = StaffPushDelivery.objects.select_for_update().get(pk=delivery.pk)
            if delivery.sent_at or delivery.attempts >= 5:
                continue
            try:
                send_firebase(device.token, notification)
            except Exception as exc:
                # Never log tokens, credential contents, or provider exception messages.
                code = type(exc).__name__[:80]
                StaffPushDelivery.objects.filter(pk=delivery.pk).update(attempts=delivery.attempts + 1, error_code=code)
                if code in {"UnregisteredError", "SenderIdMismatchError"}:
                    StaffPushDevice.objects.filter(pk=device.pk).update(is_active=False)
                logger.warning("Staff push delivery %s failed (%s)", delivery.pk, code)
            else:
                StaffPushDelivery.objects.filter(pk=delivery.pk).update(sent_at=timezone.now(), attempts=delivery.attempts + 1, error_code="")


def dispatch_notification_safely(notification_id):
    try:
        dispatch_notification(notification_id)
    except Exception as exc:
        logger.warning("Staff push notification %s deferred (%s)", notification_id, type(exc).__name__)
