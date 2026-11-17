"""Display helpers: {% load bank %}"""
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def money(value):
    """1234.5 -> '1,234.50'"""
    try:
        return f"{Decimal(str(value)):,.2f}"
    except (InvalidOperation, TypeError, ValueError):
        return value


@register.filter
def money_int(value):
    """Whole-baht part: 1234.5 -> '1,234'"""
    try:
        return f"{int(Decimal(str(value))):,}"
    except (InvalidOperation, TypeError, ValueError):
        return value


@register.filter
def money_dec(value):
    """Satang part: 1234.5 -> '50'"""
    try:
        return f"{Decimal(str(value)):.2f}".split(".")[1]
    except (InvalidOperation, TypeError, ValueError):
        return "00"


@register.filter
def acct(number):
    """Thai bank format: 0161109865 -> 016-1-10986-5"""
    s = str(number or "")
    if len(s) != 10 or not s.isdigit():
        return s
    return f"{s[:3]}-{s[3]}-{s[4:9]}-{s[9]}"


@register.filter
def initials(user):
    name = (user.get_full_name() or user.username or "?").split()
    return "".join(p[0] for p in name[:2]).upper()


@register.filter
def label(value):
    """IN_PROGRESS -> 'In progress'"""
    return str(value or "").replace("_", " ").capitalize()


@register.simple_tag(takes_context=True)
def active(context, *prefixes):
    """'is-active' if the current view name starts with any prefix."""
    match = getattr(context.get("request"), "resolver_match", None)
    name = match.view_name if match else ""
    return "is-active" if any(name.startswith(p) for p in prefixes) else ""
