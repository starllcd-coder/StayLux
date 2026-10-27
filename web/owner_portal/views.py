from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render
from reports.views import build_owner_units_dashboard
from urllib.parse import urlencode


@login_required
def owner_home(request):
    owner_profile = getattr(request.user, "owner_profile", None)
    if not owner_profile or not owner_profile.is_active:
        return HttpResponseForbidden("Owner portal is only available for active owners.")

    prop_id = owner_profile.property_id
    period = (request.GET.get("period") or "").strip().lower()
    if period not in {"daily", "weekly", "monthly", "custom"}:
        period = "monthly"

    params = {"period": period}
    if period == "custom":
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

    qs = urlencode(params)
    data = build_owner_units_dashboard(owner_profile, params)

    return render(
        request,
        "owner_portal/home.html",
        {
            "property_profile_id": prop_id,
            "dashboard": data,
            "owner_profile": owner_profile,
            "report_units": owner_profile.units.filter(
                property_profile_id=prop_id, is_active=True,
                unit_type__business_type=owner_profile.property.business_type,
            ).order_by("code"),
            "selected_period": period,
            "dashboard_querystring": qs,
        },
    )
