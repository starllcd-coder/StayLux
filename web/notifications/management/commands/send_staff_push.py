from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications.models import StaffJobNotification
from notifications.push import dispatch_notification_safely


class Command(BaseCommand):
    help = "Retry recent unread staff job push notifications (maximum five attempts per device)."

    def handle(self, **options):
        if not settings.FIREBASE_PUSH_ENABLED:
            self.stdout.write("Firebase push is disabled. No messages sent.")
            return
        for pk in StaffJobNotification.objects.filter(
            is_read=False, created_at__gte=timezone.now() - timedelta(hours=24),
        ).values_list("pk", flat=True).iterator():
            dispatch_notification_safely(pk)
        self.stdout.write("Staff push retry completed.")
