"""Signal handlers for cache invalidation."""

from typing import Any

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.core.cache import DepartureGenerationCache, StationOrderMapsCache, StationsCache
from apps.routes.models import Route, RouteSegment
from apps.stations.models import Connection, Station
from apps.trains.models import Car, Departure, Seat, Train


@receiver([post_save, post_delete], sender=Station)
def _on_station_change(sender: type[Station], instance: Station, **kwargs: Any) -> None:
    @transaction.on_commit
    def clear_caches() -> None:
        StationsCache.invalidate()


@receiver(post_save, sender=Connection)
def _on_connection_change(sender: type[Connection], instance: Connection, **kwargs: Any) -> None:
    @transaction.on_commit
    def clear_caches() -> None:
        for route_segment in instance.routesegment_set.select_related("route"):
            StationOrderMapsCache.invalidate(route_segment.route)


@receiver([post_save, post_delete], sender=Route)
def _on_route_change(sender: type[Route], instance: Route, **kwargs: Any) -> None:
    @transaction.on_commit
    def clear_caches() -> None:
        StationOrderMapsCache.invalidate(instance)


@receiver([post_save, post_delete], sender=RouteSegment)
def _on_route_segment_change(
    sender: type[RouteSegment], instance: RouteSegment, **kwargs: Any
) -> None:
    @transaction.on_commit
    def clear_caches() -> None:
        StationOrderMapsCache.invalidate(Route(pk=instance.route_id))


@receiver([post_save, post_delete], sender=Departure)
def _on_departure_change(sender: type[Departure], instance: Departure, **kwargs: Any) -> None:
    @transaction.on_commit
    def clear_caches() -> None:
        DepartureGenerationCache.incr(instance.uuid)


@receiver(post_save, sender=Train)
def _on_train_change(sender: type[Train], instance: Train, **kwargs: Any) -> None:
    @transaction.on_commit
    def clear_caches() -> None:
        for departure in instance.departures.all():
            DepartureGenerationCache.incr(departure.uuid)


@receiver(post_save, sender=Car)
def _on_car_change(sender: type[Car], instance: Car, **kwargs: Any) -> None:
    @transaction.on_commit
    def clear_caches() -> None:
        for departure in instance.train.departures.all():
            DepartureGenerationCache.incr(departure.uuid)


@receiver(post_save, sender=Seat)
def _on_seat_change(sender: type[Seat], instance: Seat, **kwargs: Any) -> None:
    @transaction.on_commit
    def clear_caches() -> None:
        for departure in instance.car.train.departures.all():
            DepartureGenerationCache.incr(departure.uuid)
