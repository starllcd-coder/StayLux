from django import template


register = template.Library()


@register.filter
def human_event_key(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return "Notification"
    text = text.replace("_", " ").replace("-", " ")
    text = " ".join(text.split())
    return text.title()

