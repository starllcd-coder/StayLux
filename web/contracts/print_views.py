from django.shortcuts import get_object_or_404, render
from django.conf import settings

from .models import Contract


def contract_agreement_view(request, contract_id: int):
    contract = get_object_or_404(
        Contract.objects.select_related("property_profile", "unit", "guest"),
        id=contract_id,
    )

    lang = (request.GET.get("lang") or "en").lower()
    template = "contracts/agreement_ar.html" if lang == "ar" else "contracts/agreement_en.html"

    return render(
        request,
        template,
        {
            "contract": contract,
            "property": contract.property_profile,
            "unit": contract.unit,
            "guest": contract.guest,
            "lang": lang,
            "media_url": settings.MEDIA_URL,
        },
    )