from django.test import TestCase
from types import SimpleNamespace

from mobile_api.permissions import IsMobileCustomer


class MobilePermissionsTests(TestCase):
    def test_has_permission_returns_false_without_mobile_customer(self):
        req = SimpleNamespace(user=SimpleNamespace(is_authenticated=True))
        perm = IsMobileCustomer()
        self.assertFalse(perm.has_permission(req, None))

    def test_has_permission_returns_true_with_mobile_customer_attr(self):
        req = SimpleNamespace(user=SimpleNamespace(is_authenticated=True, mobile_customer=SimpleNamespace()))
        perm = IsMobileCustomer()
        self.assertTrue(perm.has_permission(req, None))
