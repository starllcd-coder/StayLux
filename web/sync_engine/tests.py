from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from inventory.models import Unit, UnitType
from settings_app.models import PropertyProfile
from sync_engine.models import SyncConfig, SyncEvent, SyncEventStatus
from sync_engine.services import retry_dead_letters


class SyncEngineTests(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        User = get_user_model()
        self.user = User.objects.create_user(username="syncuser", password="pass1234")
        self.client.login(username="syncuser", password="pass1234")

    def test_sync_event_is_recorded_on_unit_create(self):
        prop = PropertyProfile.objects.create(name_en="Sync Property")
        ut = UnitType.objects.create(
            property_profile=prop,
            business_type=prop.business_type,
            name_en="Standard",
            base_rate=Decimal("10.000"),
        )
        Unit.objects.create(
            property_profile=prop,
            unit_type=ut,
            code="S-101",
            daily_price=Decimal("20.000"),
            monthly_price=Decimal("300.000"),
        )

        self.assertTrue(SyncEvent.objects.filter(model_label="inventory.unit", operation="create").exists())

    def test_sync_status_endpoint_returns_queue_counts(self):
        SyncConfig.objects.get_or_create(id=1)
        response = self.client.get("/api/sync/status/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("config", payload)
        self.assertIn("queue", payload)

    def test_sync_outbox_endpoint_returns_events(self):
        cfg, _ = SyncConfig.objects.get_or_create(id=1)
        cfg.shared_secret = "abc123"
        cfg.save(update_fields=["shared_secret", "updated_at"])
        event = SyncEvent.objects.create(
            source_node="node-a",
            model_label="inventory.unit",
            object_pk="10",
            operation="update",
            payload={"code": "A-10"},
        )

        response = self.client.get(
            "/api/sync/events/outbox/",
            HTTP_X_SYNC_SECRET="abc123",
            data={"exclude_source_node": "node-b"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["events"][0]["event_uuid"], str(event.event_uuid))

    def test_retry_dead_letters_requeues_events(self):
        ev = SyncEvent.objects.create(
            source_node="node-a",
            model_label="inventory.unit",
            object_pk="50",
            operation="create",
            payload={"code": "Z-50"},
            status=SyncEventStatus.FAILED,
            is_dead_letter=True,
            attempts=10,
        )
        changed = retry_dead_letters(limit=10)
        self.assertEqual(changed, 1)
        ev.refresh_from_db()
        self.assertFalse(ev.is_dead_letter)
        self.assertEqual(ev.status, SyncEventStatus.PENDING)
