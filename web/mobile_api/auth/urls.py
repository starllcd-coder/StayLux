from django.urls import path

from mobile_api.auth.views import (
    CustomerChangePasswordView,
    CustomerLoginView,
    CustomerMeView,
    CustomerRegisterView,
    OTPRequestView,
    OTPVerifyView,
    SocialLoginView,
    VerificationCheckView,
    VerificationRequestView,
)

app_name = "mobile_auth"

urlpatterns = [
    path("register/", CustomerRegisterView.as_view(), name="register"),
    path("login/", CustomerLoginView.as_view(), name="login"),
    path("me/", CustomerMeView.as_view(), name="me"),
    path("change-password/", CustomerChangePasswordView.as_view(), name="change-password"),
    path("otp/request/", OTPRequestView.as_view(), name="otp-request"),
    path("otp/verify/", OTPVerifyView.as_view(), name="otp-verify"),
    path("verification/request/", VerificationRequestView.as_view(), name="verification-request"),
    path("verification/check/", VerificationCheckView.as_view(), name="verification-check"),
    path("social-login/", SocialLoginView.as_view(), name="social-login"),
]
