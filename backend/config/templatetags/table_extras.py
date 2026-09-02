from typing import Any

from django import template


register = template.Library()


@register.filter
def get_item(obj: Any, key: Any) -> Any:
    """dict이면 get_item, list/tuple이면 인덱싱"""
    try:
        if isinstance(obj, dict):
            return obj.get(key)
        elif isinstance(obj, (list, tuple)):
            return obj[int(key)]
    except (TypeError, ValueError, IndexError, KeyError):
        pass
    return None


@register.filter
def mul(value: Any, arg: float) -> float:
    """곱셈 필터: value * arg"""
    try:
        return float(value) * float(arg)
    except (TypeError, ValueError):
        return 0
