from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from accounts.models import StaffProfile, OwnerProfile
from settings_app.models import PropertyProfile
from inventory.models import Unit, UnitType
from guests.models import Guest
from bookings.models import Booking


class PropertyManagementTests(TestCase):
    def setUp(self):
        self.prop = PropertyProfile.objects.create(name_en="Test Property")
        self.other = PropertyProfile.objects.create(name_en="Other Property")
        self.admin = self.staff("admin", "owner_admin")
        self.manager = self.staff("manager", "manager")
        self.reception = self.staff("reception", "reception")
        self.owner = get_user_model().objects.create_user(username="apartment_owner", password="pass")
        OwnerProfile.objects.create(user=self.owner, property=self.prop)

    def staff(self, username, role):
        user = get_user_model().objects.create_user(username=username, password="pass")
        StaffProfile.objects.create(user=user, property=self.prop, role=role)
        return user

    def test_admin_and_manager_can_edit_property(self):
        for user in [self.admin, self.manager]:
            self.client.force_login(user)
            response = self.client.post(reverse("property_edit", args=[self.prop.pk]), {
                "name_en": "Updated Property", "business_type": "hotel", "currency": "OMR", "is_active": "on",
            })
            self.assertRedirects(response, reverse("settings_page") + "?panel=property")
            self.prop.refresh_from_db()
            self.assertEqual(self.prop.name_en, "Updated Property")

    def test_staff_and_apartment_owner_cannot_edit_delete_or_use_api(self):
        for user in [self.reception, self.owner]:
            self.client.force_login(user)
            for route in ["property_edit", "property_delete"]:
                response = self.client.post(reverse(route, args=[self.prop.pk]), {"confirm_name": self.prop.name_en})
                self.assertEqual(response.status_code, 403)
            response = self.client.patch(f"/api/properties/{self.prop.pk}/", {"name_en": "Forbidden"}, content_type="application/json")
            self.assertEqual(response.status_code, 403)
        self.assertTrue(PropertyProfile.objects.filter(pk=self.prop.pk).exists())

    def test_manager_cannot_manage_other_property(self):
        self.client.force_login(self.manager)
        for route in ["property_edit", "property_delete"]:
            self.assertEqual(self.client.get(reverse(route, args=[self.other.pk])).status_code, 403)
        self.assertEqual(self.client.patch(f"/api/properties/{self.other.pk}/", {}, content_type="application/json").status_code, 404)

    def test_delete_requires_confirmation_and_keeps_user_accounts(self):
        self.client.force_login(self.admin)
        url = reverse("property_delete", args=[self.other.pk])
        response = self.client.get(url)
        self.assertContains(response, "Type the exact property name")
        response = self.client.post(url, {"confirm_name": "wrong"})
        self.assertContains(response, "Type the exact property name")
        self.assertTrue(PropertyProfile.objects.filter(pk=self.other.pk).exists())
        self.client.post(url, {"confirm_name": self.other.name_en})
        self.assertFalse(PropertyProfile.objects.filter(pk=self.other.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.admin.pk).exists())

    def test_manager_can_delete_assigned_property_and_is_logged_out(self):
        self.client.force_login(self.manager)
        response = self.client.post(reverse("property_delete", args=[self.prop.pk]), {"confirm_name": self.prop.name_en})
        self.assertRedirects(response, reverse("login"))
        self.assertFalse(PropertyProfile.objects.filter(pk=self.prop.pk).exists())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_protected_history_prevents_accidental_deletion(self):
        tier = UnitType.objects.create(property_profile=self.prop, name_en="Standard")
        unit = Unit.objects.create(property_profile=self.prop, unit_type=tier, code="101")
        guest = Guest.objects.create(property_profile=self.prop, full_name="Guest")
        Booking.objects.create(property_profile=self.prop, unit=unit, guest=guest,
                               start_date=date.today(), end_date=date.today() + timedelta(days=1), rate=10)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("property_delete", args=[self.prop.pk]), {"confirm_name": self.prop.name_en})
        self.assertContains(response, "protected records")
        self.assertTrue(PropertyProfile.objects.filter(pk=self.prop.pk).exists())

    def test_api_delete_requires_web_confirmation(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.delete(f"/api/properties/{self.other.pk}/").status_code, 405)
        self.assertTrue(PropertyProfile.objects.filter(pk=self.other.pk).exists())
