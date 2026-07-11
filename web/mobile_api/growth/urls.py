from django.urls import path

from mobile_api.growth.views import CustomerMembershipView, MembershipPlanListView, ReferralInviteView

app_name = "mobile_growth"

urlpatterns = [
    path("plans/", MembershipPlanListView.as_view(), name="membership-plans"),
    path("membership/", CustomerMembershipView.as_view(), name="customer-membership"),
    path("referrals/", ReferralInviteView.as_view(), name="referrals"),
]
