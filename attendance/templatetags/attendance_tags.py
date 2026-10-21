from django import template
import re

register = template.Library()

@register.filter(name='dict_lookup')
def dict_lookup(d, key):
    if isinstance(d, dict):
        return d.get(key)
    return None

@register.filter(name='mask_phone')
def mask_phone(phone_str):
    """Masks phone numbers to conceal sensitive contact numbers."""
    if not phone_str:
        return "-"
    phone_clean = str(phone_str).strip()
    if len(phone_clean) <= 4:
        return "****"
    # Keep prefix and last 3 digits, mask middle
    if len(phone_clean) > 8:
        prefix = phone_clean[:6]
        suffix = phone_clean[-3:]
        return f"{prefix}****{suffix}"
    return phone_clean[:2] + "****" + phone_clean[-2:]

