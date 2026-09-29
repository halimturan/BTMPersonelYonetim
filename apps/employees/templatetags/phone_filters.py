import re
from django import template

register = template.Library()


@register.filter(name='format_phone')
def format_phone(value):
    if not value:
        return ""

    # Sayı dışındaki tüm karakterleri temizle
    cleaned = re.sub(r'\D', '', str(value))

    # Eğer numara başında '0' veya '+90' ile gelirse temizlemek için (isteğe bağlı)
    if cleaned.startswith('90') and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith('0') and len(cleaned) == 11:
        cleaned = cleaned[1:]

    # Kalan 10 haneli numarayı formatla: 5321234567 -> 0532 123 45 67
    if len(cleaned) == 10:
        return f"0{cleaned[:3]} {cleaned[3:6]} {cleaned[6:8]} {cleaned[8:]}"

    # Eğer standart dışı bir uzunluktaysa ham halini döndür
    return value
