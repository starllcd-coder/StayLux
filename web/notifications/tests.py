from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase
from django.test import override_settings
from unittest.mock import patch

from accounts.models import StaffProfile
from housekeeping.models import HousekeepingTask
from inventory.models import Unit, UnitType
from maintenance.models import MaintenanceRequest
from notifications.models import StaffJobNotification, StaffPushDevice, StaffPushDelivery
from notifications.push import dispatch_notification
from settings_app.models import PropertyProfile


class AssignedJobNotificationTests(TestCase):
    def job_notification(self):
        HousekeepingTask.objects.create(property_profile=self.prop, unit=self.unit, assigned_to=self.hk)
        return StaffJobNotification.objects.get()

    def test_push_registration_and_unregister_are_private(self):
        token = "test-device-token-123456789"
        self.client.force_login(self.hk.user)
        data = {"token": token, "platform": "android"}
        self.assertEqual(self.client.post("/api/staff-push-devices/", data).status_code, 200)
        device = StaffPushDevice.objects.get()
        self.assertEqual(device.recipient, self.hk)
        self.client.force_login(self.maintenance.user)
        self.client.post("/api/staff-push-devices/unregister/", data)
        device.refresh_from_db()
        self.assertTrue(device.is_active)
        self.client.force_login(self.hk.user)
        self.client.post("/api/staff-push-devices/unregister/", data)
        device.refresh_from_db()
        self.assertFalse(device.is_active)
        self.assertEqual(self.client.get("/api/staff-push-devices/").status_code, 405)

    def test_nonstaff_cannot_register_and_device_moves_on_account_switch(self):
        user = get_user_model().objects.create_user(username="guest", password="pass")
        self.client.force_login(user)
        data = {"token": "test-device-token-123456789", "platform": "ios"}
        self.assertEqual(self.client.post("/api/staff-push-devices/", data).status_code, 403)
        self.client.force_login(self.hk.user)
        self.client.post("/api/staff-push-devices/", data)
        self.client.force_login(self.maintenance.user)
        self.client.post("/api/staff-push-devices/", data)
        self.assertEqual(StaffPushDevice.objects.count(), 1)
        self.assertEqual(StaffPushDevice.objects.get().recipient, self.maintenance)

    @override_settings(FIREBASE_PUSH_ENABLED=False)
    @patch("notifications.push.send_firebase")
    def test_disabled_push_never_calls_firebase(self, sender):
        notification = self.job_notification()
        StaffPushDevice.objects.create(recipient=self.hk, token="test-token", platform="android")
        dispatch_notification(notification.pk)
        sender.assert_not_called()
        self.assertFalse(StaffPushDelivery.objects.exists())

    @override_settings(FIREBASE_PUSH_ENABLED=True)
    @patch("notifications.push.send_firebase")
    def test_push_is_recipient_scoped_and_sent_only_once(self, sender):
        notification = self.job_notification()
        device = StaffPushDevice.objects.create(recipient=self.hk, token="target-token", platform="android")
        StaffPushDevice.objects.create(recipient=self.maintenance, token="other-token", platform="ios")
        dispatch_notification(notification.pk)
        dispatch_notification(notification.pk)
        sender.assert_called_once()
        self.assertEqual(sender.call_args.args[0], device.token)
        self.assertIsNotNone(StaffPushDelivery.objects.get().sent_at)

    @override_settings(FIREBASE_PUSH_ENABLED=True)
    @patch("notifications.push.send_firebase", side_effect=RuntimeError("private provider message"))
    def test_failed_push_is_retryable_and_inbox_remains(self, sender):
        notification = self.job_notification()
        StaffPushDevice.objects.create(recipient=self.hk, token="target-token", platform="android")
        for _ in range(7):
            dispatch_notification(notification.pk)
        delivery = StaffPushDelivery.objects.get()
        self.assertEqual(delivery.attempts, 5)
        self.assertEqual(delivery.error_code, "RuntimeError")
        self.assertIsNone(delivery.sent_at)
        self.assertTrue(StaffJobNotification.objects.filter(pk=notification.pk).exists())

    @override_settings(FIREBASE_PUSH_ENABLED=True)
    @patch("notifications.push.send_firebase")
    def test_push_skips_completed_reassigned_and_read_jobs(self, sender):
        notification = self.job_notification()
        StaffPushDevice.objects.create(recipient=self.hk, token="target-token", platform="android")
        job = notification.housekeeping_task
        job.status = "done"
        job.save()
        dispatch_notification(notification.pk)
        job.status = "pending"
        job.assigned_to = None
        job.save()
        dispatch_notification(notification.pk)
        job.assigned_to = self.hk
        job.save()
        notification.is_read = True
        notification.save()
        dispatch_notification(notification.pk)
        sender.assert_not_called()

    @override_settings(FIREBASE_PUSH_ENABLED=True)
    @patch("notifications.signals.dispatch_notification_safely")
    def test_push_is_dispatched_only_after_commit(self, sender):
        with self.captureOnCommitCallbacks(execute=True):
            notification = self.job_notification()
            sender.assert_not_called()
        sender.assert_called_once_with(notification.pk)
    def setUp(self):
        self.prop = PropertyProfile.objects.create(name_en="Test")
        tier = UnitType.objects.create(property_profile=self.prop, name_en="Standard")
        self.unit = Unit.objects.create(property_profile=self.prop, unit_type=tier, code="A 001")
        self.hk = self.staff("cleaner", "housekeeping")
        self.maintenance = self.staff("repair", "maintenance")

    def staff(self, username, role, prop=None):
        user = get_user_model().objects.create_user(username=username, password="testpass")
        return StaffProfile.objects.create(user=user, property=prop or self.prop, role=role)

    def test_creation_assignment_and_reassignment_notify_only_new_assignee(self):
        task = HousekeepingTask.objects.create(property_profile=self.prop, unit=self.unit, assigned_to=self.hk)
        message = StaffJobNotification.objects.get()
        self.assertEqual(message.recipient, self.hk)
        self.assertIn("A 001", message.message)
        task.notes = "Updated notes"
        task.save()
        self.assertEqual(StaffJobNotification.objects.count(), 1)
        other = self.staff("second", "housekeeping")
        task.assigned_to = other
        task.save(update_fields=["assigned_to", "updated_at"])
        self.assertEqual(StaffJobNotification.objects.count(), 2)
        self.assertEqual(StaffJobNotification.objects.first().recipient, other)

    def test_unassigned_maintenance_notifies_when_assigned(self):
        job = MaintenanceRequest.objects.create(property_profile=self.prop, unit=self.unit)
        self.assertFalse(StaffJobNotification.objects.exists())
        job.assigned_to = self.maintenance
        job.save(update_fields=["assigned_to", "updated_at"])
        message = StaffJobNotification.objects.get()
        self.assertEqual(message.maintenance_request, job)
        self.assertEqual(message.recipient, self.maintenance)

    def test_invalid_inactive_and_closed_assignments_do_not_notify(self):
        self.hk.is_active = False
        self.hk.save()
        HousekeepingTask.objects.create(property_profile=self.prop, unit=self.unit, assigned_to=self.hk)
        HousekeepingTask.objects.create(property_profile=self.prop, unit=self.unit, assigned_to=self.maintenance)
        MaintenanceRequest.objects.create(property_profile=self.prop, unit=self.unit, assigned_to=self.maintenance, status="resolved")
        other_prop = PropertyProfile.objects.create(name_en="Other")
        foreign = self.staff("foreign", "maintenance", other_prop)
        MaintenanceRequest.objects.create(property_profile=self.prop, unit=self.unit, assigned_to=foreign)
        self.assertFalse(StaffJobNotification.objects.exists())

    def test_notification_api_is_private_and_read_state_is_per_user(self):
        HousekeepingTask.objects.create(property_profile=self.prop, unit=self.unit, assigned_to=self.hk)
        MaintenanceRequest.objects.create(property_profile=self.prop, unit=self.unit, assigned_to=self.maintenance)
        self.client.force_login(self.hk.user)
        response = self.client.get("/api/staff-job-notifications/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        own = StaffJobNotification.objects.get(recipient=self.hk)
        foreign = StaffJobNotification.objects.get(recipient=self.maintenance)
        response = self.client.post(f"/api/staff-job-notifications/{foreign.pk}/read/")
        self.assertEqual(response.status_code, 404)
        response = self.client.post(f"/api/staff-job-notifications/{own.pk}/read/")
        self.assertEqual(response.status_code, 200)
        own.refresh_from_db()
        self.assertTrue(own.is_read)
        self.assertEqual(self.client.get("/api/staff-job-notifications/?unread=1").json(), [])
        self.client.logout()
        self.assertIn(self.client.get("/api/staff-job-notifications/").status_code, [401, 403])

    def test_transaction_rollback_does_not_leave_a_notification(self):
        try:
            with transaction.atomic():
                HousekeepingTask.objects.create(property_profile=self.prop, unit=self.unit, assigned_to=self.hk)
                raise ValueError("rollback")
        except ValueError:
            pass
        self.assertFalse(StaffJobNotification.objects.exists())

    def test_unrelated_partial_save_does_not_notify_unsaved_assignment(self):
        task = HousekeepingTask.objects.create(property_profile=self.prop, unit=self.unit)
        task.assigned_to = self.hk
        task.notes = "Only save notes"
        task.save(update_fields=["notes"])
        self.assertFalse(StaffJobNotification.objects.exists())
