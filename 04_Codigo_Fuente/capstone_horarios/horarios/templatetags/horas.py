from decimal import Decimal
from django import template
register = template.Library()

@register.filter
def horas_compactas(valor):
    """Presenta horas sin ceros decimales sobrantes ni separadores locales."""
    if valor is None: return ""
    return format(Decimal(str(valor)).normalize(), "f")
