from collections.abc import Callable
from typing import Any

from django.db.models import Model, QuerySet


def use_prefetched_if_available[T: Model](
    model: T,
    related_name: str,
    build_fallback_queryset: Callable[[QuerySet[Any]], QuerySet[Any]],
) -> QuerySet[Any]:
    """Return a queryset that uses the prefetched related objects if available."""
    qs = getattr(model, related_name)
    if related_name in getattr(model, "_prefetched_objects_cache", {}):
        result: QuerySet[Any] = qs.all()
        return result
    return build_fallback_queryset(qs)
