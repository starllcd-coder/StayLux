from django.shortcuts import get_object_or_404, render
from django.conf import settings
from .models import Invoice
from settings_app.models import PropertyProfile
from django.contrib.auth.decorators import login_required
from core.permissions import require_roles, ROLES_BILLING


@login_required
@require_roles(ROLES_BILLING)
def invoice_print_view(request, invoice_id: int):
    invoices = Invoice.objects.select_related("property_profile", "guest", "booking").prefetch_related("lines", "payments")
    if not request.user.is_superuser:
        invoices = invoices.filter(property_profile_id=request.user.staff_profile.property_id)
    invoice = get_object_or_404(
        invoices,
        id=invoice_id,
    )
    prop: PropertyProfile = invoice.property_profile

    lang = (request.GET.get("lang") or "en").lower()
    auto = (request.GET.get("auto") or "") == "1"
    template = "billing/invoice_print_ar.html" if lang == "ar" else "billing/invoice_print.html"

    return render(
        request,
        template,
        {
            "invoice": invoice,
            "property": prop,
            "media_url": settings.MEDIA_URL,
            "lang": lang,
            "auto": auto,
        },
    )
