from django.db.models import QuerySet

from apps.core.cache import StationOrderMaps, StationOrderMapsCache
from apps.core.db_utils import use_prefetched_if_available
from apps.routes.exceptions import InvalidStationRangeError
from apps.routes.models import Route, RouteSegment


def get_route_segments(route: Route) -> QuerySet[RouteSegment]:
    """Return a queryset of the route's segments, prefetched if available."""
    return use_prefetched_if_available(
        route,
        "route_segments",
        lambda qs: qs.select_related("segment"),
    )


@StationOrderMapsCache.wrap
def get_station_order_maps(route: Route) -> StationOrderMaps:
    """Return ``(from_order_by_station, to_order_by_station)`` for a route.

    ``from_order_by_station[station_id]`` is the order of the first segment
    whose ``station_from`` is that station. ``to_order_by_station[station_id]``
    is ``order + 1`` for the first segment whose ``station_to`` is that
    station. Cached per-process by ``route.pk`` and invalidated via signals
    when the route's segments change.
    """
    from_map: dict[int, int] = {}
    to_map: dict[int, int] = {}
    for route_segment in get_route_segments(route):
        from_map.setdefault(route_segment.segment.station_from_id, route_segment.order)
        to_map.setdefault(route_segment.segment.station_to_id, route_segment.order + 1)
    return from_map, to_map


def resolve_station_range(
    route: Route, station_from_id: int, station_to_id: int
) -> tuple[int, int]:
    """
    Return ``(from_order, to_order)`` for a trip along ``route``.
    Raises :class:`InvalidStationRangeError` if the stations are invalid or in the wrong order.
    Uses the cached station-order maps built by :func:`get_station_order_maps`.
    """
    from_map, to_map = get_station_order_maps(route)
    f = from_map.get(station_from_id)
    t = to_map.get(station_to_id)
    if f is None or t is None or t <= f:
        raise InvalidStationRangeError()
    return f, t
