from decimal import Decimal, ROUND_HALF_UP

from django import template

register = template.Library()


@register.filter
def currency3(value):
    try:
        dec = Decimal(str(value or "0"))
        return dec.quantize(Decimal("0.000"), rounding=ROUND_HALF_UP)
    except Exception:
        return value
