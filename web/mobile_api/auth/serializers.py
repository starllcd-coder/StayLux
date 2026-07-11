from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError
from rest_framework import serializers

from mobile_api.auth.models import MobileCustomer

User = get_user_model()


class MobileCustomerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = MobileCustomer
        fields = [
            "id",
            "full_name",
            "email",
            "mobile",
            "preferred_language",
            "preferred_country",
            "loyalty_points",
            "loyalty_tier",
            "referral_code",
            "auth_provider",
            "external_subject",
            "is_verified",
            "email_verified_at",
            "phone_verified",
            "two_factor_enabled",
            "marketing_opt_in",
            "email_notifications_enabled",
            "push_notifications_enabled",
            "sms_notifications_enabled",
            "is_active",
            "last_login_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "auth_provider",
            "external_subject",
            "loyalty_points",
            "loyalty_tier",
            "referral_code",
            "is_verified",
            "email_verified_at",
            "phone_verified",
            "two_factor_enabled",
            "is_active",
            "last_login_at",
            "created_at",
            "updated_at",
        ]


class CustomerRegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    mobile = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    preferred_language = serializers.ChoiceField(
        choices=MobileCustomer.PreferredLanguage.choices,
        required=False,
        default=MobileCustomer.PreferredLanguage.EN,
    )
    preferred_country = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
        default="",
    )
    marketing_opt_in = serializers.BooleanField(required=False, default=False)

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate_mobile(self, value):
        return value.strip()

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        full_name = validated_data["full_name"].strip()
        email = validated_data["email"].strip().lower()
        mobile = validated_data.get("mobile", "").strip()
        password = validated_data["password"]
        preferred_language = validated_data.get(
            "preferred_language",
            MobileCustomer.PreferredLanguage.EN,
        )
        preferred_country = validated_data.get("preferred_country", "").strip()
        marketing_opt_in = validated_data.get("marketing_opt_in", False)

        username_base = email
        username = username_base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{username_base}-{counter}"
            counter += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=full_name,
        )

        customer = MobileCustomer.objects.create(
            user=user,
            full_name=full_name,
            mobile=mobile,
            preferred_language=preferred_language,
            preferred_country=preferred_country,
            marketing_opt_in=marketing_opt_in,
            auth_provider=MobileCustomer.AuthProvider.EMAIL,
        )
        return customer


class CustomerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        password = attrs["password"]

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise serializers.ValidationError({"email": "No account found with this email."})

        authenticated_user = authenticate(
            request=self.context.get("request"),
            username=user.username,
            password=password,
        )
        if not authenticated_user:
            raise serializers.ValidationError({"password": "Invalid email or password."})

        try:
            if not hasattr(authenticated_user, "mobile_customer"):
                raise serializers.ValidationError({"email": "This account is not a mobile customer account."})
            customer = authenticated_user.mobile_customer
        except (OperationalError, ProgrammingError):
            raise serializers.ValidationError(
                {"detail": "Mobile database schema is outdated. Please run migrations and retry login."}
            )
        if not customer.is_active:
            raise serializers.ValidationError({"email": "This customer account is inactive."})

        attrs["user"] = authenticated_user
        attrs["customer"] = customer
        return attrs


class CustomerProfileUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", required=False)
    full_name = serializers.CharField(required=False)
    mobile = serializers.CharField(required=False, allow_blank=True)
    preferred_language = serializers.ChoiceField(
        choices=MobileCustomer.PreferredLanguage.choices,
        required=False,
    )
    preferred_country = serializers.CharField(required=False, allow_blank=True)
    marketing_opt_in = serializers.BooleanField(required=False)
    email_notifications_enabled = serializers.BooleanField(required=False)
    push_notifications_enabled = serializers.BooleanField(required=False)
    sms_notifications_enabled = serializers.BooleanField(required=False)

    class Meta:
        model = MobileCustomer
        fields = [
            "full_name",
            "mobile",
            "preferred_language",
            "preferred_country",
            "marketing_opt_in",
            "email_notifications_enabled",
            "push_notifications_enabled",
            "sms_notifications_enabled",
            "email",
        ]

    def validate_email(self, value):
        request = self.context["request"]
        email = value.strip().lower()
        qs = User.objects.filter(email__iexact=email).exclude(id=request.user.id)
        if qs.exists():
            raise serializers.ValidationError("Another account already uses this email.")
        return email

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        email = user_data.get("email")
        if email is not None:
            instance.user.email = email.strip().lower()
            instance.user.save(update_fields=["email"])

        return instance


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        request = self.context["request"]
        user = request.user

        current_password = attrs["current_password"]
        new_password = attrs["new_password"]
        confirm_new_password = attrs["confirm_new_password"]

        if not user.check_password(current_password):
            raise serializers.ValidationError({"current_password": "Current password is incorrect."})

        if new_password != confirm_new_password:
            raise serializers.ValidationError({"confirm_new_password": "Passwords do not match."})

        if current_password == new_password:
            raise serializers.ValidationError({"new_password": "New password must be different."})

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user


class OTPRequestSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=50)

    def validate_mobile(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Mobile number is required.")
        return value


class OTPVerifySerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=50)
    otp = serializers.CharField(max_length=10)

    def validate_mobile(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Mobile number is required.")
        return value

    def validate_otp(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("OTP is required.")
        return value


class SocialLoginSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(
        choices=[
            MobileCustomer.AuthProvider.GOOGLE,
            MobileCustomer.AuthProvider.APPLE,
        ]
    )
    id_token = serializers.CharField()
    full_name = serializers.CharField(required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True)


class VerificationRequestSerializer(serializers.Serializer):
    purpose = serializers.ChoiceField(
        choices=[
            ("email_verify", "email_verify"),
            ("two_factor", "two_factor"),
        ]
    )
    channel = serializers.ChoiceField(choices=[("email", "email"), ("sms", "sms")], required=False, default="email")


class VerificationCheckSerializer(serializers.Serializer):
    purpose = serializers.ChoiceField(
        choices=[
            ("email_verify", "email_verify"),
            ("two_factor", "two_factor"),
        ]
    )
    code = serializers.CharField(max_length=10)
