from typing import TYPE_CHECKING

from django.db.models import Model, QuerySet

if TYPE_CHECKING:
    from collections.abc import Callable


def is_prefetched(model: Model, related_name: str) -> bool:
    """Return True if the related objects for ``related_name`` are prefetched."""
    return related_name in getattr(model, "_prefetched_objects_cache", {})


def use_prefetched_if_available[T: Model, R: Model](
    model: T,
    related_name: str,
    build_fallback_queryset: Callable[[QuerySet[R]], QuerySet[R]],
) -> QuerySet[R]:
    """Return a queryset that uses the prefetched related objects if available."""
    qs: QuerySet[R] = getattr(model, related_name)
    if is_prefetched(model, related_name):
        return qs.all()
    return build_fallback_queryset(qs)
