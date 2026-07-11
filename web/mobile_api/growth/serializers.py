from rest_framework import serializers

from mobile_api.growth.models import CustomerMembership, MembershipPlan, ReferralInvite


class MembershipPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipPlan
        fields = ["id", "name", "monthly_fee", "annual_fee", "benefits", "is_active"]


class CustomerMembershipSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = CustomerMembership
        fields = ["id", "plan", "plan_name", "status", "started_at", "renews_at", "created_at"]
        read_only_fields = ["status", "started_at", "renews_at", "created_at"]


class ReferralInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralInvite
        fields = ["id", "referred_email", "status", "reward_points", "created_at"]
        read_only_fields = ["status", "reward_points", "created_at"]
