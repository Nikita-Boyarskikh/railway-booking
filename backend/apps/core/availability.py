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

from psycopg.types.range import Range

from apps.bookings.models import Booking
from apps.core.db_utils import is_prefetched
from apps.trains.models import Departure, Seat

SEGMENT_RANGE_BOUNDS = "[)"


def make_segment_range(from_order: int, to_order: int) -> Range[int]:
    """Build a half-open ``[from_order, to_order)`` range for segment overlap checks."""
    return Range(from_order, to_order, bounds=SEGMENT_RANGE_BOUNDS)


def free_seat_ids(departure: Departure, from_order: int, to_order: int) -> set[int]:
    """Return the set of seat IDs free on ``departure`` for the given range."""
    if is_prefetched(departure.train, "cars"):
        all_seat_ids = {seat.pk for car in departure.train.cars.all() for seat in car.seats.all()}
    else:
        all_seat_ids = set(
            Seat.objects.filter(car__train=departure.train).values_list("id", flat=True)
        )
    trip_range = make_segment_range(from_order, to_order)
    occupied = set(
        Booking.objects.filter(departure=departure, segment_range__overlap=trip_range).values_list(
            "seat_id", flat=True
        )
    )
    return all_seat_ids - occupied
