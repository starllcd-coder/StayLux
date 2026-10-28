from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test import override_settings
from cryptography.fernet import Fernet
from django.urls import reverse
from accounts.models import StaffProfile, OwnerProfile
from inventory.models import Unit, UnitType
from settings_app.models import PropertyProfile, ChannelIntegration


class ChannelSettingsTests(TestCase):
    def credential_payload(self):
        return {"agoda-external_property_id": "HOTEL123", "agoda-authentication_method": "api_token",
                "agoda-access_token": "private-api-test-token",
                f"agoda-unit_{self.unit.pk}_room": "ROOM456"}

    @override_settings(CHANNEL_CREDENTIALS_KEY="")
    def test_credentials_refused_without_encryption_key(self):
        response = self.client.post(reverse("channel_integration_save", args=["agoda"]), self.credential_payload(), follow=True)
        self.assertContains(response, "Secure credential storage is not configured")
        self.assertFalse(ChannelIntegration.objects.exists())
        self.assertNotContains(response, "private-api-test-token")

    def test_encrypted_credentials_are_preserved_and_never_echoed(self):
        with override_settings(CHANNEL_CREDENTIALS_KEY=Fernet.generate_key().decode()):
            url = reverse("channel_integration_save", args=["agoda"])
            response = self.client.post(url, self.credential_payload(), follow=True)
            saved = ChannelIntegration.objects.get(platform="agoda")
            self.assertNotIn("private-api-test-token", saved.credentials_encrypted)
            self.assertEqual(saved.get_credentials()["access_token"], "private-api-test-token")
            self.assertNotContains(response, "private-api-test-token")
            self.assertNotContains(response, saved.credentials_encrypted)
            data = self.credential_payload()
            data["agoda-access_token"] = ""
            data["action"] = "check_setup"
            response = self.client.post(url, data, follow=True)
            self.assertContains(response, "Local setup checks passed")
            self.assertContains(response, "Live authorization and synchronization still require")
            saved.refresh_from_db()
            self.assertEqual(saved.get_credentials()["access_token"], "private-api-test-token")
            data["agoda-clear_credentials"] = "on"
            self.client.post(url, data)
            saved.refresh_from_db()
            self.assertEqual(saved.credentials_encrypted, "")

    def test_setup_check_reports_missing_values(self):
        response = self.client.post(reverse("channel_integration_save", args=["agoda"]), {"action": "check_setup"}, follow=True)
        self.assertContains(response, "Enter the external property / hotel ID.")
        self.assertContains(response, "Map at least one room or listing.")
        self.assertContains(response, "Supply the API credentials")
    def setUp(self):
        self.prop = PropertyProfile.objects.create(name_en="Property")
        self.other = PropertyProfile.objects.create(name_en="Other")
        self.manager = self.user("manager", "manager")
        tier = UnitType.objects.create(property_profile=self.prop, name_en="Standard")
        self.unit = Unit.objects.create(property_profile=self.prop, unit_type=tier, code="A 001")
        self.client.force_login(self.manager)

    def user(self, name, role):
        user = get_user_model().objects.create_user(username=name, password="pass")
        StaffProfile.objects.create(user=user, property=self.prop, role=role)
        return user

    def test_tab_order_platforms_and_honest_connection_status(self):
        response = self.client.get(reverse("settings_page") + "?panel=integrations")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertLess(html.index('data-tab="tab-backup"'), html.index('data-tab="tab-integrations"'))
        for name in ["Agoda", "Booking.com", "Airbnb"]:
            self.assertContains(response, name)
        self.assertContains(response, "Not configured", count=3)
        self.assertContains(response, "Setup only")
        self.assertFalse(ChannelIntegration.objects.exists())

    def test_each_platform_saves_only_its_own_property_metadata(self):
        session = self.client.session
        session["active_property_id"] = self.other.pk
        session.save()
        for platform in ["agoda", "booking", "airbnb"]:
            response = self.client.post(reverse("channel_integration_save", args=[platform]), {
                f"{platform}-external_property_id": "HOTEL123",
                f"{platform}-account_reference": "Account reference",
                f"{platform}-unit_{self.unit.pk}_room": "ROOM456",
                f"{platform}-unit_{self.unit.pk}_rate": "RATE789",
                f"{platform}-unit_99999_room": "not-my-unit",
                "property_profile": self.other.pk,
            })
            self.assertRedirects(response, reverse("settings_page") + "?panel=integrations")
            saved = ChannelIntegration.objects.get(platform=platform)
            self.assertEqual(saved.property_profile, self.prop)
            self.assertEqual(saved.external_property_id, "HOTEL123")
            self.assertEqual(saved.unit_mappings, {str(self.unit.pk): {"room_id": "ROOM456", "rate_plan_id": "RATE789"}})

    def test_other_roles_cannot_save_and_invalid_platform_is_rejected(self):
        url = reverse("channel_integration_save", args=["agoda"])
        for role in ["accounts", "reception", "housekeeping", "maintenance"]:
            self.client.force_login(self.user(role, role))
            self.assertEqual(self.client.post(url, {}).status_code, 403)
        owner = get_user_model().objects.create_user(username="apartment_owner", password="pass")
        OwnerProfile.objects.create(user=owner, property=self.prop)
        self.client.force_login(owner)
        self.assertEqual(self.client.post(url, {}).status_code, 403)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(reverse("channel_integration_save", args=["unknown"]), {}).status_code, 404)
        self.assertFalse(ChannelIntegration.objects.exists())
