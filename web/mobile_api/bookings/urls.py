from django.urls import path

from mobile_api.bookings.views import (
    BookingCreateView,
    BookingQuoteView,
    CustomerBookingCancelView,
    CustomerBookingDetailView,
    CustomerBookingListView,
    PaymentIntentCreateView,
    PaymentRecordListView,
    PaymentSecurityConfigView,
    PaymentVerifyView,
)

app_name = "mobile_bookings"

urlpatterns = [
    path("quote/", BookingQuoteView.as_view(), name="booking-quote"),
    path("create/", BookingCreateView.as_view(), name="booking-create"),
    path("my/", CustomerBookingListView.as_view(), name="booking-list"),
    path("<int:id>/", CustomerBookingDetailView.as_view(), name="booking-detail"),
    path("<int:id>/cancel/", CustomerBookingCancelView.as_view(), name="booking-cancel"),
    path("payments/intent/", PaymentIntentCreateView.as_view(), name="payment-intent"),
    path("payments/history/", PaymentRecordListView.as_view(), name="payment-history"),
    path("payments/<int:id>/verify/", PaymentVerifyView.as_view(), name="payment-verify"),
    path("payments/security-config/", PaymentSecurityConfigView.as_view(), name="payment-security-config"),
]
