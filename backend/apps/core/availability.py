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

from collections import defaultdict
from typing import TYPE_CHECKING

from apps.bookings.models import Booking
from apps.core.db_utils import is_prefetched
from apps.core.pricing import calc_segment_range_subtotal
from apps.routes.exceptions import InvalidStationRangeError
from apps.routes.services import resolve_station_range
from apps.trains.models import Departure, Seat

if TYPE_CHECKING:
    from djmoney.money import Money


def free_seat_ids(departure: Departure, from_order: int, to_order: int) -> set[int]:
    """Return the set of seat IDs free on ``departure`` for the given range."""
    if is_prefetched(departure.train, "cars"):
        all_seat_ids = {seat.pk for car in departure.train.cars.all() for seat in car.seats.all()}
    else:
        all_seat_ids = set(
            Seat.objects.filter(car__train=departure.train).values_list("id", flat=True)
        )
    trip_range = Booking.make_segment_range(from_order, to_order)
    occupied = set(
        Booking.objects.filter(departure=departure, segment_range__overlap=trip_range).values_list(
            "seat_id", flat=True
        )
    )
    return all_seat_ids - occupied


def batch_occupied_seat_ids_with_subtotal(
    departures: list[Departure], from_station_id: int, to_station_id: int
) -> dict[int, tuple[set[int], Money]]:
    """Return ``{departure_id: {occupied_seat_ids}}`` for many departures in one query."""
    route_by_id = {}
    departure_ids_by_route_id: dict[int, set[int]] = defaultdict(set)
    for departure in departures:
        route_by_id[departure.train.route_id] = departure.train.route
        departure_ids_by_route_id[departure.train.route_id].add(departure.pk)

    result = {}
    for route_id, departure_ids in departure_ids_by_route_id.items():
        route = route_by_id[route_id]
        try:
            from_order, to_order = resolve_station_range(route, from_station_id, to_station_id)
        except InvalidStationRangeError:
            continue

        trip_range = Booking.make_segment_range(from_order, to_order)

        rows = Booking.objects.filter(
            departure_id__in=departure_ids,
            segment_range__overlap=trip_range,
        ).values_list("departure_id", "seat_id")

        subtotal = calc_segment_range_subtotal(route, from_order, to_order)

        seats_by_departure_id: dict[int, set[int]] = defaultdict(set)
        for departure_id, seat_id in rows:
            seats_by_departure_id[departure_id].add(seat_id)

        # Include all departures for this route, even those with zero bookings.
        for departure_id in departure_ids:
            result[departure_id] = (seats_by_departure_id[departure_id], subtotal)
    return result
