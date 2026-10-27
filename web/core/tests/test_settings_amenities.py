from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.core.management import call_command
from io import StringIO

from inventory.models import Amenity, UnitType
from settings_app.models import PropertyProfile
from inventory.amenity_names import AMENITY_AR_NAMES
from inventory.text import repair_arabic_encoding


class SettingsAmenitiesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("admin", "admin@example.com", "testpass")
        self.client.force_login(self.user)
        self.prop = PropertyProfile.objects.create(name_en="Hotel")
        self.other = PropertyProfile.objects.create(name_en="Other")
        session = self.client.session
        session["active_property_id"] = self.prop.pk
        session.save()
        self.url = reverse("settings_page")
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def add(self, name):
        return self.client.post(self.url, {
            "form_kind": "amenity_add", "amenity-name_en": name,
            "amenity-is_active": "on",
        })

    def test_duplicate_add_and_update_show_errors(self):
        amenity = Amenity.objects.filter(property_profile=self.prop).first()
        response = self.add(amenity.name_en)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        other = Amenity.objects.create(property_profile=self.prop, name_en="Custom")
        response = self.client.post(self.url, {
            "form_kind": "amenity_update", "amenity_id": other.pk,
            "name_en": amenity.name_en, "is_active": "true",
        }, follow=True)
        self.assertContains(response, "already exists")
        other.refresh_from_db()
        self.assertEqual(other.name_en, "Custom")

    def test_deleted_default_stays_deleted(self):
        amenity = Amenity.objects.filter(property_profile=self.prop).first()
        name = amenity.name_en
        response = self.client.post(self.url, {
            "form_kind": "amenity_delete", "amenity_id": amenity.pk,
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.client.get(self.url)
        self.assertFalse(Amenity.objects.filter(property_profile=self.prop, name_en=name).exists())

    def test_custom_and_renamed_amenities_can_be_selected(self):
        self.assertRedirects(self.add("Rooftop pool"), self.url + "?panel=amenities")
        amenity = Amenity.objects.get(property_profile=self.prop, name_en="Rooftop pool")
        response = self.client.post(self.url, {
            "form_kind": "amenity_update", "amenity_id": amenity.pk,
            "name_en": "Roof pool", "name_ar": "", "is_active": "true",
        }, follow=True)
        for tier in response.context["tier_tabs"]:
            self.assertIn(amenity.pk, [a["id"] for a in tier["hotel_items"]])

    def test_tier_save_scopes_property_mode_and_active_amenities(self):
        active = Amenity.objects.create(property_profile=self.prop, name_en="Custom")
        inactive = Amenity.objects.create(property_profile=self.prop, name_en="Inactive", is_active=False)
        foreign = Amenity.objects.create(property_profile=self.other, name_en="Foreign")
        response = self.client.post(self.url, {
            "form_kind": "tier_amenities", "tier_name": "Deluxe", "mode_key": "hotel",
            "amenity_ids": [active.pk, inactive.pk, foreign.pk],
        }, follow=True)
        tier = UnitType.objects.get(property_profile=self.prop, business_type="hotel", name_en="Deluxe")
        self.assertEqual(list(tier.amenities.all()), [active])
        selected = next(t for t in response.context["tier_tabs"] if t["name"] == "Deluxe")
        self.assertTrue(next(a for a in selected["hotel_items"] if a["id"] == active.pk)["checked"])
        self.assertNotIn(inactive.pk, [a["id"] for a in selected["hotel_items"]])
        response = self.client.post(self.url, {
            "form_kind": "tier_amenities", "tier_name": "Deluxe", "mode_key": "apartments",
        })
        self.assertEqual(response.status_code, 400)
        self.client.post(self.url, {
            "form_kind": "tier_amenities", "tier_name": "Deluxe", "mode_key": "hotel",
        })
        self.assertFalse(tier.amenities.exists())

    def test_cannot_edit_or_delete_another_property_amenity(self):
        foreign = Amenity.objects.create(property_profile=self.other, name_en="Foreign")
        for action in ["amenity_update", "amenity_delete"]:
            response = self.client.post(self.url, {"form_kind": action, "amenity_id": foreign.pk})
            self.assertEqual(response.status_code, 404)

    def test_blank_name_has_visible_validation(self):
        response = self.add("")
        self.assertContains(response, "This field is required")

    def test_arabic_defaults_render_without_encoding_corruption(self):
        response = self.client.get(self.url + "?panel=amenities")
        expected = "\u062a\u0643\u064a\u064a\u0641"
        self.assertEqual(AMENITY_AR_NAMES["Air conditioning"], expected)
        self.assertContains(response, expected)
        self.assertContains(response, 'dir="rtl"')
        for label in AMENITY_AR_NAMES.values():
            self.assertNotIn("\u00d8", label)
            self.assertNotIn("\u00d9", label)

    def test_repair_command_preserves_custom_arabic_and_is_repeatable(self):
        expected = AMENITY_AR_NAMES["Air conditioning"]
        broken = expected.encode("utf-8").decode("cp1252", errors="surrogateescape")
        broken = "".join(chr(ord(c) - 0xdc00) if 0xdc80 <= ord(c) <= 0xdcff else c for c in broken)
        self.assertEqual(repair_arabic_encoding(broken), expected)
        amenity = Amenity.objects.get(property_profile=self.prop, name_en="Air conditioning")
        amenity.name_ar = broken
        amenity.save()
        custom = Amenity.objects.create(property_profile=self.prop, name_en="Custom", name_ar="\u0645\u0633\u0628\u062d")
        call_command("populate_amenity_ar", commit=True, stdout=StringIO())
        amenity.refresh_from_db()
        custom.refresh_from_db()
        self.assertEqual(amenity.name_ar, expected)
        self.assertEqual(custom.name_ar, "\u0645\u0633\u0628\u062d")
        output = StringIO()
        call_command("populate_amenity_ar", commit=True, stdout=output)
        self.assertIn("Mapped 0 amenities", output.getvalue())

    def test_no_property_keeps_input_and_explains_why_add_cannot_save(self):
        PropertyProfile.objects.all().delete()
        response = self.add("Wifi")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_panel"], "amenities")
        self.assertContains(response, "Create a property in the Property tab")
        self.assertContains(response, 'value="Wifi"')
        self.assertFalse(Amenity.objects.exists())

    def test_successful_add_lands_on_amenities_with_saved_name(self):
        response = self.client.post(self.url + "?panel=amenities", {
            "form_kind": "amenity_add", "amenity-name_en": "Wifi", "amenity-is_active": "on",
        }, follow=True)
        self.assertEqual(response.context["active_panel"], "amenities")
        self.assertContains(response, 'value="Wifi"')
        self.assertTrue(Amenity.objects.filter(property_profile=self.prop, name_en="Wifi").exists())

    def test_dropdown_add_preserves_existing_and_remove_only_unlinks(self):
        amenities = list(Amenity.objects.filter(property_profile=self.prop)[:2])
        data = {"form_kind": "tier_amenity_add", "tier_name": "Premium", "mode_key": "hotel"}
        for amenity in amenities:
            response = self.client.post(self.url, {**data, "amenity_id": amenity.pk}, follow=True)
            self.assertEqual(response.status_code, 200)
        self.client.post(self.url, {**data, "amenity_id": amenities[0].pk})
        tier = UnitType.objects.get(property_profile=self.prop, business_type="hotel", name_en="Premium")
        self.assertEqual(tier.amenities.count(), 2)
        context_tier = next(t for t in response.context["tier_tabs"] if t["name"] == "Premium")
        self.assertEqual(set(context_tier["selected_amenities"]), set(amenities))
        self.assertNotIn(amenities[0], context_tier["available_amenities"])
        self.assertContains(response, "Save to Tier")
        self.client.post(self.url, {**data, "form_kind": "tier_amenity_remove", "amenity_id": amenities[0].pk})
        self.assertEqual(list(tier.amenities.all()), [amenities[1]])
        self.assertTrue(Amenity.objects.filter(pk=amenities[0].pk).exists())

    def test_dropdown_rejects_invalid_property_inactive_and_wrong_mode(self):
        inactive = Amenity.objects.create(property_profile=self.prop, name_en="Inactive", is_active=False)
        foreign = Amenity.objects.create(property_profile=self.other, name_en="Foreign")
        data = {"form_kind": "tier_amenity_add", "tier_name": "Luxury", "mode_key": "hotel"}
        for extra, status in [
            ({"amenity_id": inactive.pk}, 400),
            ({"amenity_id": foreign.pk}, 404),
            ({"amenity_id": ""}, 400),
            ({"amenity_id": inactive.pk, "mode_key": "apartments"}, 400),
        ]:
            self.assertEqual(self.client.post(self.url, {**data, **extra}).status_code, status)

    def test_apartments_save_independently(self):
        self.prop.business_type = "apartments"
        self.prop.save()
        amenity = Amenity.objects.filter(property_profile=self.prop, is_active=True).first()
        response = self.client.post(self.url, {
            "form_kind": "tier_amenities", "tier_name": "Standard", "mode_key": "apartments",
            "amenity_ids": [amenity.pk],
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        hotel = UnitType.objects.get(property_profile=self.prop, business_type="hotel", name_en="Standard")
        apartments = UnitType.objects.get(property_profile=self.prop, business_type="apartments", name_en="Standard")
        self.assertFalse(hotel.amenities.exists())
        self.assertEqual(list(apartments.amenities.all()), [amenity])
