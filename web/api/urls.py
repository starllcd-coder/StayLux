from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import StaffProfileViewSet
from billing.views import InvoiceViewSet, PaymentViewSet
from bookings.views import BookingViewSet
from contracts.views import ContractDocumentViewSet, ContractViewSet
from guests.views import GuestViewSet
from housekeeping.views import HousekeepingTaskViewSet
from inspections.views import MoveOutInspectionViewSet
from inventory.views import AmenityViewSet, UnitTypeViewSet, UnitViewSet
from maintenance.views import MaintenanceRequestViewSet
from notifications.views import NotificationSettingViewSet, OutboxMessageViewSet, WhatsAppTemplateViewSet
from notifications.views import StaffJobNotificationViewSet
from notifications.views import StaffPushDeviceViewSet
from pricing.views import (
    AvailabilitySuggestionView,
    BulkSeasonalRateUpdateView,
    DynamicPricingRuleViewSet,
    DynamicPricingSuggestionView,
    RatePlanViewSet,
    SeasonalRateRuleViewSet,
)
from settings_app.views import PropertyProfileViewSet

router = DefaultRouter()
router.register(r"staff-job-notifications", StaffJobNotificationViewSet, basename="staff-job-notifications")
router.register(r"staff-push-devices", StaffPushDeviceViewSet, basename="staff-push-devices")
router.register(r"properties", PropertyProfileViewSet, basename="property")
router.register(r"staff", StaffProfileViewSet, basename="staff")
router.register(r"amenities", AmenityViewSet, basename="amenity")
router.register(r"unit-types", UnitTypeViewSet, basename="unit-type")
router.register(r"units", UnitViewSet, basename="unit")
router.register(r"guests", GuestViewSet, basename="guest")
router.register(r"rate-plans", RatePlanViewSet, basename="rate-plan")
router.register(r"seasonal-rates", SeasonalRateRuleViewSet, basename="seasonal-rate")
router.register(r"dynamic-pricing-rules", DynamicPricingRuleViewSet, basename="dynamic-pricing-rule")
router.register(r"bookings", BookingViewSet, basename="booking")
router.register(r"contracts", ContractViewSet, basename="contract")
router.register(r"contract-documents", ContractDocumentViewSet, basename="contract-document")
router.register(r"moveout-inspections", MoveOutInspectionViewSet, basename="moveout-inspection")
router.register(r"invoices", InvoiceViewSet, basename="invoice")
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"housekeeping", HousekeepingTaskViewSet, basename="housekeeping")
router.register(r"maintenance", MaintenanceRequestViewSet, basename="maintenance")
router.register(r"notification-settings", NotificationSettingViewSet, basename="notification-settings")
router.register(r"whatsapp-templates", WhatsAppTemplateViewSet, basename="whatsapp-templates")
router.register(r"outbox", OutboxMessageViewSet, basename="outbox")

urlpatterns = [
    path("", include(router.urls)),
    path("pricing/suggestions/", DynamicPricingSuggestionView.as_view(), name="pricing-suggestions"),
    path("pricing/availability-suggestions/", AvailabilitySuggestionView.as_view(), name="pricing-availability-suggestions"),
    path("pricing/bulk-seasonal-update/", BulkSeasonalRateUpdateView.as_view(), name="pricing-bulk-seasonal-update"),
    path("reports/", include("reports.urls")),
    path("sync/", include("sync_engine.urls")),
]
