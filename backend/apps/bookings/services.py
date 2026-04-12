"""Service layer for the bookings app: order creation and validation."""

from typing import TYPE_CHECKING

from constance import config
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from djmoney.money import Money

from apps.bookings.exceptions import DepartureNotFoundError, SeatNotFoundError, SeatUnavailableError
from apps.bookings.models import BOOKING_NO_OVERLAP_CONSTRAINT, Booking, Order, Passenger
from apps.core.availability import make_segment_range
from apps.core.cache import DepartureGenerationCache
from apps.core.db_utils import populate_prefetched_objects_cache
from apps.core.pricing import calc_booking_price, calc_segment_range_subtotal
from apps.routes.services import resolve_station_range
from apps.stations.services import resolve_station_codes
from apps.trains.models import Departure, Seat, Train

if TYPE_CHECKING:
    import uuid as uuid_mod

    from apps.core.types import OrderItemInput


def get_seat(train: Train, car_number: int, seat_number: int) -> Seat:
    """Check that a seat exists on the train and is available for booking."""
    try:
        seat = Seat.objects.select_related("car__train__route").get(
            car__train=train,
            car__number=car_number,
            number=seat_number,
        )
    except Seat.DoesNotExist as e:
        raise SeatNotFoundError(car_number, seat_number) from e
    return seat


@transaction.atomic
def create_order(
    departure_uuid: str | uuid_mod.UUID,
    station_from_code: str,
    station_to_code: str,
    items: list[OrderItemInput],
) -> Order:
    """Create an :class:`Order` with one :class:`Booking` per ``item``.

    Concurrency safety is delegated to a GiST ``ExclusionConstraint`` on
    ``Booking`` that forbids two bookings for the same ``(departure, seat)``
    from holding overlapping ``segment_range`` values. The constraint covers
    both cross-transaction races and duplicate seats in a single order, so
    this function does not take any row-level locks — it just inserts and
    translates the resulting ``IntegrityError`` into
    :class:`SeatUnavailableError`.

    Input validation (empty items, same station, field types) is expected
    to be handled by the serializer layer before calling this function.

    Raises:
        DepartureNotFoundError: If departure with given uuid does not exist.
        SeatNotFoundError: If a requested seat is not found in this train.
        SeatUnavailableError: If a requested seat is already booked for the range.
    """
    try:
        departure = (
            Departure.objects.select_related("train__route")
            .prefetch_related(
                "train__route__route_segments__connection",
            )
            .get(uuid=departure_uuid)
        )
    except (Departure.DoesNotExist, ValidationError) as e:
        raise DepartureNotFoundError() from e

    station_from, station_to = resolve_station_codes(station_from_code, station_to_code)

    route = departure.train.route
    from_order, to_order = resolve_station_range(route, station_from.pk, station_to.pk)
    trip_range = make_segment_range(from_order, to_order)

    # Subtotal depends only on (route, from_order, to_order), so compute it
    # once for all items instead of repeating the RouteSegment scan per seat.
    base_price = Money(config.BASE_PRICE, currency=settings.DEFAULT_CURRENCY)
    subtotal = calc_segment_range_subtotal(route, from_order, to_order)

    # Sort items by (car_number, seat_number) so two concurrent multi-seat
    # orders on overlapping seat sets always touch rows in the same order and
    # cannot deadlock on the exclusion-constraint index.
    sorted_items = sorted(items, key=lambda i: (i["car_number"], i["seat_number"]))

    resolved: list[tuple[OrderItemInput, Seat]] = []
    total = Money(0, settings.DEFAULT_CURRENCY)

    for item in sorted_items:
        seat = get_seat(departure.train, item["car_number"], item["seat_number"])
        resolved.append((item, seat))
        total += calc_booking_price(base_price, subtotal, seat)

    # Total is known up-front, so insert the order with its final price in a
    # single statement rather than INSERT followed by UPDATE.
    order = Order.objects.create(total_price=total)

    bookings: list[Booking] = []
    for item, seat in resolved:
        passenger_data = item["passenger"]
        passenger = Passenger.objects.create(
            name=passenger_data["name"],
            passport_number=passenger_data["passport_number"],
            gender=passenger_data["gender"],
            birth_date=passenger_data["birth_date"],
        )

        try:
            booking = Booking.objects.create(
                order=order,
                departure=departure,
                seat=seat,
                station_from=station_from,
                station_to=station_to,
                passenger=passenger,
                segment_range=trip_range,
            )
        except IntegrityError as e:
            if BOOKING_NO_OVERLAP_CONSTRAINT not in str(e):  # pragma: no cover
                raise  # should never happen if the DB schema is correct
            raise SeatUnavailableError(seat.car.number, seat.number) from e
        bookings.append(booking)

    # Populate prefetch cache so the caller can serialize without extra queries.
    # All FK objects (departure, seat.car, station_from, station_to, passenger)
    # are already loaded in memory from the creation above.
    populate_prefetched_objects_cache(order, "bookings", bookings)

    transaction.on_commit(lambda: DepartureGenerationCache.incr(departure.uuid))

    return order
