from typing import Any

from django import template


register = template.Library()


@register.filter
def get_item(value: Any, key: Any) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    if isinstance(value, (list, tuple)):
        try:
            return value[int(key)]
        except (TypeError, ValueError, IndexError):
            return None
    return None
