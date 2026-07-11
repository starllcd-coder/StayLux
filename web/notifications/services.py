from __future__ import annotations
from typing import Dict, Any

from .models import NotificationSetting, WhatsAppTemplate, OutboxMessage, Channel


DEFAULT_TEMPLATES_EN = {
    "invoice_issued": "Hello {guest_name}, your invoice {invoice_no} is issued. Total: {total} OMR. Balance: {balance} OMR.",
    "payment_received": "Hello {guest_name}, payment received for invoice {invoice_no}. Paid: {paid_amount} OMR. Balance: {balance} OMR.",
}


def _render_template(text: str, context: Dict[str, Any]) -> str:
    try:
        return text.format(**context)
    except Exception:
        # If placeholders missing, return raw text to avoid crashing
        return text


def queue_event_message(property_profile, event_key: str, to_phone: str, context: Dict[str, Any], language: str = "en") -> OutboxMessage | None:
    """
    Phase A: store messages in outbox (DB). Later connect to WhatsApp provider.
    """
    if not to_phone:
        return None

    setting, _ = NotificationSetting.objects.get_or_create(property_profile=property_profile)
    if not setting.enable_whatsapp:
        return None

    # Try property template first
    tmpl = WhatsAppTemplate.objects.filter(
        property_profile=property_profile, key=event_key, language=language, is_active=True
    ).first()

    body = (tmpl.body if tmpl else DEFAULT_TEMPLATES_EN.get(event_key, f"{event_key}: " + "{guest_name}"))
    content = _render_template(body, context)

    msg = OutboxMessage.objects.create(
        property_profile=property_profile,
        channel=Channel.WHATSAPP,
        to_phone=to_phone,
        event_key=event_key,
        language=language,
        content=content,
    )
    return msg