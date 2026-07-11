from datetime import timedelta
import random

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone

from mobile_api.auth.serializers import (
    ChangePasswordSerializer,
    CustomerLoginSerializer,
    CustomerProfileUpdateSerializer,
    CustomerRegisterSerializer,
    MobileCustomerSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    SocialLoginSerializer,
    VerificationCheckSerializer,
    VerificationRequestSerializer,
)
from mobile_api.auth.models import MobileVerificationCode
from mobile_api.auth.services import build_customer_token_payload, get_or_create_social_customer
from mobile_api.permissions import IsMobileCustomer


class CustomerRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = CustomerRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = serializer.save()
        token_data = build_customer_token_payload(customer.user)

        return Response(
            {
                "message": "Customer account created successfully.",
                "customer": MobileCustomerSerializer(customer).data,
                "tokens": token_data,
            },
            status=status.HTTP_201_CREATED,
        )


class CustomerLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = CustomerLoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        customer = serializer.validated_data["customer"]
        customer.mark_login()
        token_data = build_customer_token_payload(customer.user)

        return Response(
            {
                "message": "Login successful.",
                "customer": MobileCustomerSerializer(customer).data,
                "tokens": token_data,
            },
            status=status.HTTP_200_OK,
        )


class CustomerMeView(APIView):
    permission_classes = [IsMobileCustomer]

    def get(self, request, *args, **kwargs):
        customer = request.user.mobile_customer
        return Response(MobileCustomerSerializer(customer).data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        customer = request.user.mobile_customer
        serializer = CustomerProfileUpdateSerializer(
            customer,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MobileCustomerSerializer(customer).data, status=status.HTTP_200_OK)


class CustomerChangePasswordView(APIView):
    permission_classes = [IsMobileCustomer]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )


class OTPRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Placeholder implementation for single-phase structure.
        # Real SMS provider integration should be added in deployment stage.
        return Response(
            {
                "message": "OTP request accepted.",
                "mobile": serializer.validated_data["mobile"],
                "provider_status": "pending_provider_integration",
            },
            status=status.HTTP_200_OK,
        )


class OTPVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Placeholder verification flow.
        return Response(
            {
                "message": "OTP verification endpoint is ready.",
                "mobile": serializer.validated_data["mobile"],
                "verification_status": "pending_provider_integration",
            },
            status=status.HTTP_200_OK,
        )


class SocialLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = SocialLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Placeholder token validation for Google/Apple.
        # Real provider verification must be added with Google/Apple SDK validation.
        provider = serializer.validated_data["provider"]
        full_name = serializer.validated_data.get("full_name", "")
        email = serializer.validated_data.get("email", "") or ""
        id_token = serializer.validated_data["id_token"]

        customer = get_or_create_social_customer(
            provider=provider,
            email=email,
            full_name=full_name,
            external_subject=id_token[:100],
        )
        customer.mark_login()
        token_data = build_customer_token_payload(customer.user)

        return Response(
            {
                "message": f"{provider.title()} login successful.",
                "customer": MobileCustomerSerializer(customer).data,
                "tokens": token_data,
                "provider_validation": "placeholder_implementation",
            },
            status=status.HTTP_200_OK,
        )


class VerificationRequestView(APIView):
    permission_classes = [IsMobileCustomer]

    def post(self, request, *args, **kwargs):
        serializer = VerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = request.user.mobile_customer
        purpose = serializer.validated_data["purpose"]
        channel = serializer.validated_data["channel"]
        target = customer.email if channel == "email" else customer.mobile
        code = f"{random.randint(100000, 999999)}"
        MobileVerificationCode.objects.create(
            customer=customer,
            purpose=purpose,
            channel=channel,
            target=target or "",
            code=code,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        payload = {"message": "Verification code generated.", "purpose": purpose, "channel": channel}
        if settings.DEBUG:
            payload["dev_code"] = code
        return Response(payload, status=status.HTTP_200_OK)


class VerificationCheckView(APIView):
    permission_classes = [IsMobileCustomer]

    def post(self, request, *args, **kwargs):
        serializer = VerificationCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = request.user.mobile_customer
        purpose = serializer.validated_data["purpose"]
        code = serializer.validated_data["code"].strip()
        row = (
            MobileVerificationCode.objects.filter(
                customer=customer,
                purpose=purpose,
                code=code,
                is_used=False,
            )
            .order_by("-created_at")
            .first()
        )
        if not row or row.expires_at <= timezone.now():
            return Response({"detail": "Invalid or expired code."}, status=status.HTTP_400_BAD_REQUEST)
        row.is_used = True
        row.save(update_fields=["is_used", "updated_at"])
        if purpose == MobileVerificationCode.Purpose.EMAIL_VERIFY:
            customer.is_verified = True
            customer.email_verified_at = timezone.now()
            customer.save(update_fields=["is_verified", "email_verified_at", "updated_at"])
        elif purpose == MobileVerificationCode.Purpose.TWO_FACTOR:
            customer.two_factor_enabled = True
            customer.save(update_fields=["two_factor_enabled", "updated_at"])
        return Response({"message": "Verification successful.", "purpose": purpose}, status=status.HTTP_200_OK)
