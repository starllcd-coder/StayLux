import json
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.test import Client
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

    data = None
    c = Client()
    c.force_login(request.user)
    qs = urlencode(params)
    res = c.get(f"/api/reports/owner-dashboard/?{qs}")
    if res.status_code == 200:
        data = json.loads(res.content.decode("utf-8"))

    return render(
        request,
        "owner_portal/home.html",
        {
            "property_profile_id": prop_id,
            "dashboard": data,
            "owner_profile": owner_profile,
            "selected_period": period,
            "dashboard_querystring": qs,
        },
    )
