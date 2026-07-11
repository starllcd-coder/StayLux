from rest_framework import serializers

from mobile_api.auth.models import MobileCustomer
from mobile_api.auth.serializers import MobileCustomerSerializer
from mobile_api.profile.models import MobilePaymentMethod, TravelerProfile


class TravelerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelerProfile
        fields = [
            "id",
            "full_name",
            "phone",
            "whatsapp",
            "email",
            "nationality",
            "id_type",
            "id_number",
            "id_expiry",
            "address",
            "notes",
            "is_default",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class TravelerProfileCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TravelerProfile
        fields = [
            "full_name",
            "phone",
            "whatsapp",
            "email",
            "nationality",
            "id_type",
            "id_number",
            "id_expiry",
            "address",
            "notes",
            "is_default",
            "is_active",
        ]


class CustomerProfileDetailSerializer(serializers.Serializer):
    customer = MobileCustomerSerializer()
    travelers = TravelerProfileSerializer(many=True)
    payment_methods = serializers.SerializerMethodField()

    def get_payment_methods(self, obj):
        methods = obj.get("payment_methods", [])
        return MobilePaymentMethodSerializer(methods, many=True).data


class MobilePaymentMethodSerializer(serializers.ModelSerializer):
    masked_number = serializers.SerializerMethodField()

    class Meta:
        model = MobilePaymentMethod
        fields = [
            "id",
            "brand",
            "last4",
            "masked_number",
            "exp_month",
            "exp_year",
            "is_default",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "masked_number"]

    def get_masked_number(self, obj):
        return f"**** **** **** {obj.last4}"


class MobilePaymentMethodCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobilePaymentMethod
        fields = [
            "brand",
            "last4",
            "exp_month",
            "exp_year",
            "provider_token",
            "is_default",
        ]


class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileCustomer
        fields = [
            "marketing_opt_in",
            "email_notifications_enabled",
            "push_notifications_enabled",
            "sms_notifications_enabled",
        ]

class CustomerProfileSummarySerializer(serializers.ModelSerializer):
    traveler_count = serializers.SerializerMethodField()

    class Meta:
        model = MobileCustomer
        fields = [
            "id",
            "full_name",
            "mobile",
            "preferred_language",
            "preferred_country",
            "traveler_count",
        ]

    def get_traveler_count(self, obj):
        return obj.travelers.filter(is_active=True).count()
