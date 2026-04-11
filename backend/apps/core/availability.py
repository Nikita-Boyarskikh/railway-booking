"""Seat availability helpers.

Request-path callers translate public ``(station_from_code, station_to_code)``
inputs into an internal ``(from_order, to_order)`` range over the train's
``RouteSegment.order`` values. The translation is driven by a per-route pair
of maps from ``station_id`` to segment order, cached in an in-memory cache
keyed by ``route.pk`` and invalidated by signal handlers in
:mod:`apps.core.signals` whenever a ``Route`` or ``RouteSegment`` row changes.

Overlap checks on existing bookings are delegated to Postgres via the GiST
exclusion constraint on ``Booking`` — :func:`free_seat_ids` derives the
occupied set with a single ``segment_range &&`` query rather than walking
route segments in Python.
"""

from django.db.models import QuerySet
from psycopg.types.range import Range

from apps.bookings.models import Booking
from apps.core.cache import _StationOrderMaps, cached_station_order_maps
from apps.core.db_utils import use_prefetched_if_available, is_prefetched
from apps.routes.models import Route, RouteSegment
from apps.trains.models import Departure, Seat


def _get_station_order_maps(route: Route) -> _StationOrderMaps:
    """Return ``(from_order_by_station, to_order_by_station)`` for a route.

    ``from_order_by_station[station_id]`` is the order of the first segment
    whose ``station_from`` is that station. ``to_order_by_station[station_id]``
    is ``order + 1`` for the first segment whose ``station_to`` is that
    station. Cached per-process by ``route.pk`` and invalidated via signals
    when the route's segments change.
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
    return from_map, to_map


def resolve_station_range(
    route: Route, station_from_id: int, station_to_id: int
) -> tuple[int, int] | None:
    """Return ``(from_order, to_order)`` for a trip along ``route`` or ``None``.

    Uses the cached station-order maps built by :func:`_get_station_order_maps`.
    """
    from_map, to_map = cached_station_order_maps(route, _get_station_order_maps)
    f = from_map.get(station_from_id)
    t = to_map.get(station_to_id)
    if f is None or t is None or t <= f:
        return None
    return f, t


def free_seat_ids(departure: Departure, from_order: int, to_order: int) -> set[int]:
    """Return the set of seat IDs free on ``departure`` for the given range.

    Two queries regardless of how many existing bookings there are: at most
    one for all seats on the train (skipped if already prefetched with
    ``prefetch_related("train__cars__seats")``) and one
    ``segment_range && [from_order, to_order)`` over the bookings for this
    departure. The overlap test runs in Postgres against the GiST index that
    backs the exclusion constraint.
    """
    if is_prefetched(departure.train, "cars"):
        all_seat_ids = {seat.pk for car in departure.train.cars.all() for seat in car.seats.all()}
    else:
        all_seat_ids = set(
            Seat.objects.filter(car__train=departure.train).values_list("id", flat=True)
        )
    trip_range: Range[int] = Range(from_order, to_order, bounds="[)")
    occupied = set(
        Booking.objects.filter(departure=departure, segment_range__overlap=trip_range).values_list(
            "seat_id", flat=True
        )
    )
    return all_seat_ids - occupied
