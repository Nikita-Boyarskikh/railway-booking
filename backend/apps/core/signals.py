"""Signal handlers for cache invalidation."""

from typing import Any

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.cache import StationOrderMapsCache, StationsCache
from apps.routes.models import Route, RouteSegment
from apps.stations.models import Station


@receiver([post_save, post_delete], sender=Station)
def _invalidate_stations_cache(sender: type[Station], **kwargs: Any) -> None:
    """Drop the cached station list whenever a Station row changes.

    Wrapped in ``transaction.on_commit`` so that if the enclosing transaction
    rolls back, the cache is not invalidated against non-existent state.
    """
    transaction.on_commit(lambda: StationsCache.invalidate())


@receiver([post_save, post_delete], sender=RouteSegment)
def _invalidate_order_maps_on_segment_change(
    sender: type[RouteSegment], instance: RouteSegment, **kwargs: Any
) -> None:
    """Drop the cached station-order maps for the affected route."""
    transaction.on_commit(lambda: StationOrderMapsCache.invalidate(instance.route))


@receiver([post_save, post_delete], sender=Route)
def _invalidate_order_maps_on_route_change(
    sender: type[Route], instance: Route, **kwargs: Any
) -> None:
    """Drop the cached station-order maps when a Route itself changes."""
    transaction.on_commit(lambda: StationOrderMapsCache.invalidate(instance))
