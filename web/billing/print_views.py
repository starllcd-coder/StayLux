from django.shortcuts import get_object_or_404, render
from django.conf import settings
from .models import Invoice
from settings_app.models import PropertyProfile


def invoice_print_view(request, invoice_id: int):
    invoice = get_object_or_404(
        Invoice.objects.select_related("property_profile", "guest", "booking").prefetch_related("lines", "payments"),
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