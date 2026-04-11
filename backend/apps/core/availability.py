"""Seat availability helpers.

Availability is derived dynamically from the ``Booking`` table by comparing
segment-order ranges along a route. To keep this cheap, we build once per
route a pair of maps from ``(station_from_id, station_to_id)`` to the
``RouteSegment.order`` at which that station first appears, and cache them
on the ``Route`` instance.
"""

from functools import cache

from django.db.models import QuerySet

from apps.bookings.models import Booking
from apps.core.db_utils import use_prefetched_if_available
from apps.routes.models import Route, RouteSegment
from apps.trains.models import Departure, Seat


@cache
def _get_station_order_maps(route: Route) -> tuple[dict[int, int], dict[int, int]]:
    """Return ``(from_order_by_station, to_order_by_station)`` for a route.

    ``from_order_by_station[station_id]`` is the order of the first segment
    whose ``station_from`` is that station. ``to_order_by_station[station_id]``
    is ``order + 1`` for the first segment whose ``station_to`` is that
    station. Cached by ``functools.cache`` on the route's identity (pk-based).
    """
    from_map: dict[int, int] = {}
    to_map: dict[int, int] = {}
    route_segments: QuerySet[RouteSegment] = use_prefetched_if_available(
        route,
        "route_segments",
        lambda qs: qs.select_related("segment__station_from", "segment__station_to"),
    )
    for route_segment in route_segments:
        from_map.setdefault(route_segment.segment.station_from_id, route_segment.order)
        to_map.setdefault(route_segment.segment.station_to_id, route_segment.order + 1)

    return (from_map, to_map)


def resolve_station_range(
    route: Route, station_from_id: int, station_to_id: int
) -> tuple[int, int] | None:
    """Return ``(from_order, to_order)`` for a trip along ``route`` or ``None``.

    Uses the cached station-order maps built by :func:`_get_station_order_maps`.
    """
    from_map, to_map = _get_station_order_maps(route)
    f = from_map.get(station_from_id)
    t = to_map.get(station_to_id)
    if f is None or t is None or t <= f:
        return None
    return f, t


def seat_is_free(departure: Departure, seat_id: int, from_order: int, to_order: int) -> bool:
    """Return True if no existing booking overlaps ``[from_order, to_order)``."""
    route = departure.train.route
    existing = Booking.objects.filter(departure=departure, seat_id=seat_id).only(
        "seat_id", "station_from_id", "station_to_id", "departure_id"
    )
    for b in existing:
        b_from, b_to = resolve_station_range(route, b.station_from_id, b.station_to_id) or (0, 0)
        if b_from < to_order and from_order < b_to:
            return False
    return True


def free_seat_ids(departure: Departure, from_order: int, to_order: int) -> set[int]:
    """Return the set of seat IDs free on ``departure`` for the given range.

    Runs in O(1) DB queries regardless of how many existing bookings there are:
    one query for all seats on the train, one for all bookings on the
    departure. Overlap checks are resolved in Python via cached route maps.
    """
    all_seat_ids = set(Seat.objects.filter(car__train=departure.train).values_list("id", flat=True))
    route = departure.train.route
    occupied: set[int] = set()
    bookings = Booking.objects.filter(departure=departure).values_list(
        "seat_id", "station_from_id", "station_to_id"
    )
    for seat_id, sf, st in bookings:
        rng = resolve_station_range(route, sf, st)
        assert rng is not None, "booking with invalid station_from/station_to for route"
        b_from, b_to = rng
        if b_from < to_order and from_order < b_to:
            occupied.add(seat_id)
    return all_seat_ids - occupied
