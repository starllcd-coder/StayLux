from django.test import TestCase
from django.contrib.auth import get_user_model


class MobileCannotAccessStaffViews(TestCase):
    def test_mobile_user_cannot_access_bookings_list(self):
        User = get_user_model()
        user = User.objects.create_user(username="mobile_user", password="pass")
        # Authenticate as a regular user (no staff_profile / owner_profile)
        self.client.force_login(user)

        resp = self.client.get("/bookings/")

        # Staff-only views should redirect non-staff authenticated users (dashboard)
        self.assertEqual(resp.status_code, 302)
