from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from mobile_api.growth.models import CustomerMembership, MembershipPlan, ReferralInvite
from mobile_api.growth.serializers import (
    CustomerMembershipSerializer,
    MembershipPlanSerializer,
    ReferralInviteSerializer,
)
from mobile_api.permissions import IsMobileCustomer


class MembershipPlanListView(APIView):
    permission_classes = [IsMobileCustomer]

    def get(self, request, *args, **kwargs):
        qs = MembershipPlan.objects.filter(is_active=True)
        return Response(MembershipPlanSerializer(qs, many=True).data, status=status.HTTP_200_OK)


class CustomerMembershipView(APIView):
    permission_classes = [IsMobileCustomer]

    def get(self, request, *args, **kwargs):
        qs = CustomerMembership.objects.filter(customer=request.user.mobile_customer).order_by("-created_at")
        return Response(CustomerMembershipSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        plan_id = request.data.get("plan_id")
        plan = MembershipPlan.objects.filter(id=plan_id, is_active=True).first()
        if not plan:
            return Response({"plan_id": "Plan not found."}, status=status.HTTP_400_BAD_REQUEST)
        now = timezone.now()
        membership = CustomerMembership.objects.create(
            customer=request.user.mobile_customer,
            plan=plan,
            started_at=now,
            renews_at=now + timedelta(days=30),
        )
        return Response(CustomerMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class ReferralInviteView(APIView):
    permission_classes = [IsMobileCustomer]

    def get(self, request, *args, **kwargs):
        qs = ReferralInvite.objects.filter(referrer=request.user.mobile_customer)
        return Response(ReferralInviteSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        email = (request.data.get("email") or "").strip().lower()
        if not email or "@" not in email:
            return Response({"email": "Valid email required."}, status=status.HTTP_400_BAD_REQUEST)
        invite = ReferralInvite.objects.create(referrer=request.user.mobile_customer, referred_email=email)
        return Response(ReferralInviteSerializer(invite).data, status=status.HTTP_201_CREATED)
