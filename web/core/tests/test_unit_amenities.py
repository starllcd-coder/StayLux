from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.forms import UnitForm, UnitTypeForm
from inventory.models import Amenity, Unit, UnitType
from settings_app.models import PropertyProfile


class UnitAmenitiesTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("admin", "admin@example.com", "pass"))
        self.prop = PropertyProfile.objects.create(name_en="Test")
        session = self.client.session
        session["active_property_id"] = self.prop.pk
        session.save()
        self.tier = UnitType.objects.create(property_profile=self.prop, name_en="Standard")
        self.amenity = Amenity.objects.create(property_profile=self.prop, name_en="Wifi")
        self.inactive = Amenity.objects.create(property_profile=self.prop, name_en="Inactive", is_active=False)
        other = PropertyProfile.objects.create(name_en="Other")
        self.foreign = Amenity.objects.create(property_profile=other, name_en="Foreign")

    def data(self, **extra):
        return dict(unit_type=self.tier.pk, code="101", category="single", guest_capacity=1,
                    daily_price=0, monthly_price=0, seasonal_price=0, status="available",
                    is_active="on", amenities=[self.amenity.pk], **extra)

    def test_checkbox_choices_and_labels_render(self):
        for form in [UnitForm(property_obj=self.prop), UnitTypeForm(property_obj=self.prop)]:
            html = str(form["amenities"])
            self.assertIn('type="checkbox"', html)
            self.assertIn('value="%s"' % self.amenity.pk, html)
            self.assertIn("Wifi", html)
            self.assertNotIn("Foreign", html)
            self.assertNotIn("Inactive", html)
            self.assertNotIn('class="form-check-input"', html)
        response = self.client.get(reverse("unit_create"))
        self.assertNotContains(response, 'name="amenities"')
        self.assertNotIn("amenities", response.context["form"].fields)

    def test_create_and_edit_persist_amenities_in_both_modes(self):
        self.tier.amenities.add(self.amenity, self.inactive)
        for mode, category in [("hotel", "single"), ("apartments", Unit.UnitCategory.STUDIO_APT)]:
            with self.subTest(mode=mode):
                self.prop.business_type = mode
                self.prop.save()
                self.tier.business_type = mode
                self.tier.save()
                data = self.data()
                data.update(code=mode, category=category)
                response = self.client.post(reverse("unit_create"), data)
                self.assertEqual(response.status_code, 302, response.context["form"].errors if response.status_code == 200 else "")
                unit = Unit.objects.get(code=mode)
                self.assertEqual(list(unit.amenities.all()), [self.amenity])
                data["amenities"] = []
                response = self.client.post(reverse("unit_edit", args=[unit.pk]), data)
                self.assertEqual(response.status_code, 302)
                self.assertFalse(unit.amenities.exists())

    def test_rejects_foreign_and_inactive_amenities(self):
        for amenity in [self.foreign, self.inactive]:
            data = self.data()
            data["amenities"] = [amenity.pk]
            form = UnitForm(data, property_obj=self.prop)
            self.assertFalse(form.is_valid())
            self.assertIn("amenities", form.errors)

    def test_validation_failure_keeps_amenity_checkboxes_hidden(self):
        data = self.data()
        data["code"] = ""
        response = self.client.post(reverse("unit_create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("amenities", response.context["form"].fields)
        self.assertNotContains(response, 'name="amenities"')

    def test_tier_endpoint_returns_saved_selections(self):
        self.tier.amenities.add(self.amenity)
        response = self.client.get(reverse("unit_type_amenities", args=[self.tier.pk]))
        self.assertEqual(response.json(), {"amenity_ids": [self.amenity.pk]})

    def test_list_uses_current_tier_amenities_for_existing_units(self):
        unit = Unit.objects.create(property_profile=self.prop, unit_type=self.tier, code="101")
        self.assertFalse(unit.amenities.exists())
        self.tier.amenities.add(self.amenity, self.inactive)
        response = self.client.get(reverse("units_list"))
        self.assertContains(response, "Wifi")
        self.assertNotContains(response, ">Inactive</span>")
        self.tier.amenities.remove(self.amenity)
        response = self.client.get(reverse("units_list"))
        self.assertNotContains(response, "Wifi")
        self.assertContains(response, "No amenities configured for this tier.")

    def test_create_ignores_posted_amenities_and_uses_tier(self):
        self.tier.amenities.add(self.amenity)
        data = self.data()
        data["amenities"] = [self.foreign.pk]
        response = self.client.post(reverse("unit_create"), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(Unit.objects.get(code="101").amenities.all()), [self.amenity])
