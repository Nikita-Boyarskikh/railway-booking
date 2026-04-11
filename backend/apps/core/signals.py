"""Signal handlers for cache invalidation."""

from typing import Any

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.routes.models import Route, RouteSegment
from apps.stations.models import Station

from .cache import invalidate_station_order_maps, invalidate_stations


@receiver([post_save, post_delete], sender=Station)
def _invalidate_stations_cache(sender: type[Station], **kwargs: Any) -> None:
    """Drop the cached station list whenever a Station row changes.

    Wrapped in ``transaction.on_commit`` so that if the enclosing transaction
    rolls back, the cache is not invalidated against non-existent state.
    """
    transaction.on_commit(invalidate_stations)


@receiver([post_save, post_delete], sender=RouteSegment)
def _invalidate_order_maps_on_segment_change(
    sender: type[RouteSegment], instance: RouteSegment, **kwargs: Any
) -> None:
    """Drop the cached station-order maps for the affected route."""
    route_id = instance.route_id
    transaction.on_commit(lambda: invalidate_station_order_maps(route_id))


@receiver([post_save, post_delete], sender=Route)
def _invalidate_order_maps_on_route_change(
    sender: type[Route], instance: Route, **kwargs: Any
) -> None:
    """Drop the cached station-order maps when a Route itself changes."""
    route_id = instance.pk
    transaction.on_commit(lambda: invalidate_station_order_maps(route_id))
