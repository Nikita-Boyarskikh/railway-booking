"""Seat availability helpers.

Availability is derived dynamically from the ``Booking`` table by comparing
segment-order ranges along a route. To keep this cheap, we build once per
route a pair of maps from ``(station_from_id, station_to_id)`` to the
``RouteSegment.order`` at which that station first appears, and cache them
on the ``Route`` instance.
"""

from __future__ import annotations


def _get_station_order_maps(route) -> tuple[dict[int, int], dict[int, int]]:
    """Return ``(from_order_by_station, to_order_by_station)`` for a route.

    ``from_order_by_station[station_id]`` is the order of the first segment
    whose ``station_from`` is that station. ``to_order_by_station[station_id]``
    is ``order + 1`` for the first segment whose ``station_to`` is that
    station. Maps are cached on ``route._station_orders_cache``.
    """
    cache = getattr(route, "_station_orders_cache", None)
    if cache is not None:
        return cache

    from_map: dict[int, int] = {}
    to_map: dict[int, int] = {}
    # Reuse any prefetched route_segments to avoid extra queries; otherwise
    # run a single select_related query.
    if "route_segments" in getattr(route, "_prefetched_objects_cache", {}):
        rss = sorted(route.route_segments.all(), key=lambda rs: rs.order)
    else:
        rss = list(route.route_segments.select_related("segment").order_by("order"))
    for rs in rss:
        seg = rs.segment
        if seg.station_from_id not in from_map:
            from_map[seg.station_from_id] = rs.order
        if seg.station_to_id not in to_map:
            to_map[seg.station_to_id] = rs.order + 1

    cache = (from_map, to_map)
    route._station_orders_cache = cache
    return cache


def resolve_station_range(
    route, station_from_id: int, station_to_id: int
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


def booking_segment_range(booking) -> tuple[int, int]:
    """Resolve a booking's ``(from_order, to_order)`` via cached route maps."""
    route = booking.departure.train.route
    rng = resolve_station_range(route, booking.station_from_id, booking.station_to_id)
    return rng if rng else (0, 0)


def seat_is_free(departure, seat_id: int, from_order: int, to_order: int) -> bool:
    """Return True if no existing booking overlaps ``[from_order, to_order)``."""
    from apps.bookings.models import Booking

    route = departure.train.route
    _get_station_order_maps(route)  # warm cache once.
    existing = Booking.objects.filter(departure=departure, seat_id=seat_id).only(
        "seat_id", "station_from_id", "station_to_id", "departure_id"
    )
    for b in existing:
        b_from, b_to = resolve_station_range(route, b.station_from_id, b.station_to_id) or (0, 0)
        if b_from < to_order and from_order < b_to:
            return False
    return True


def free_seat_ids(departure, from_order: int, to_order: int) -> set[int]:
    """Return the set of seat IDs free on ``departure`` for the given range.

    Runs in O(1) DB queries regardless of how many existing bookings there are:
    one query for all seats on the train, one for all bookings on the
    departure. Overlap checks are resolved in Python via cached route maps.
    """
    from apps.bookings.models import Booking
    from apps.trains.models import Seat

    all_seat_ids = set(Seat.objects.filter(car__train=departure.train).values_list("id", flat=True))
    route = departure.train.route
    _get_station_order_maps(route)
    occupied: set[int] = set()
    bookings = Booking.objects.filter(departure=departure).values_list(
        "seat_id", "station_from_id", "station_to_id"
    )
    for seat_id, sf, st in bookings:
        rng = resolve_station_range(route, sf, st)
        if not rng:
            continue
        b_from, b_to = rng
        if b_from < to_order and from_order < b_to:
            occupied.add(seat_id)
    return all_seat_ids - occupied
