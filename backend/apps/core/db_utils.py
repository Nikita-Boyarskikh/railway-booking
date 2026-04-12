from collections.abc import Callable
from typing import Any

from django.db.models import Model, QuerySet


def is_prefetched(model: Model, related_name: str) -> bool:
    """Return True if the related objects for ``related_name`` are prefetched."""
    return related_name in getattr(model, "_prefetched_objects_cache", {})


def use_prefetched_if_available[T: Model](
    model: T,
    related_name: str,
    build_fallback_queryset: Callable[[QuerySet[Any]], QuerySet[Any]],
) -> QuerySet[Any]:
    """Return a queryset that uses the prefetched related objects if available."""
    qs = getattr(model, related_name)
    if is_prefetched(model, related_name):
        result: QuerySet[Any] = qs.all()
        return result
    return build_fallback_queryset(qs)


def populate_prefetched_objects_cache[T: Model, R: Model](
    model: T, related_name: str, objects: Iterable[R]
) -> None:
    """Populate the prefetched objects cache."""
    if not hasattr(model, "_prefetched_objects_cache"):
        model._prefetched_objects_cache = {}
    model._prefetched_objects_cache[related_name] = objects
    model._prefetch_done = True
