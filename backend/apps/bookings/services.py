"""Service layer for the bookings app: order creation and validation."""
import uuid as uuid_mod

from constance import config
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _
from djmoney.money import Money
from psycopg.types.range import Range

from apps.bookings.models import BOOKING_NO_OVERLAP_CONSTRAINT, Booking, Order, Passenger
from apps.core.cache import DepartureGenerationCache
from apps.core.pricing import calc_booking_price, calc_segment_range_subtotal
from apps.core.types import OrderItemInput
from apps.routes.services import resolve_station_range
from apps.stations.services import resolve_station_codes
from apps.trains.models import Departure, Seat, Train
from config.settings import DEFAULT_CURRENCY


class SeatUnavailableError(Exception):
    """Raised when a requested seat was taken between validation and commit."""

    def __init__(self, car_number: int, seat_number: int):
        super().__init__(
            _("Seat car={car_number} seat={seat_number} no longer available").format(
                seat_number=seat_number,
                car_number=car_number,
            )
        )
        self.car_number = car_number
        self.seat_number = seat_number


class InvalidRequestError(Exception):
    """Raised for business-logic errors during order creation (maps to 400)."""


def get_seat(train: Train, car_number: int, seat_number: int) -> Seat:
    """Check that a seat exists on the train and is available for booking."""
    try:
        seat = Seat.objects.select_related("car__train__route").get(
            car__train=train,
            car__number=car_number,
            number=seat_number,
        )
    except Seat.DoesNotExist as e:
        raise InvalidRequestError(
            _("Seat car={car_number} seat={seat_number} not found on this train").format(
                car_number=car_number,
                seat_number=seat_number,
            )
        ) from e
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
        InvalidRequestError: On unknown references or route mismatch.
        SeatUnavailableError: If a requested seat is already booked for the range.
    """
    try:
        departure = Departure.objects.select_related("train__route").prefetch_related(
            "train__route__route_segments__segment",
        ).get(uuid=departure_uuid)
    except (Departure.DoesNotExist, ValidationError) as e:
        raise InvalidRequestError(_("Departure not found")) from e

    station_from, station_to = resolve_station_codes(station_from_code, station_to_code)
    if not station_from or not station_to:
        raise InvalidRequestError(_("Unknown station code"))

    route = departure.train.route
    from_order, to_order = resolve_station_range(route, station_from.pk, station_to.pk)
    if not from_order and not to_order:
        raise InvalidRequestError(
            _("Route does not cover the requested station_from → station_to segment")
        )
    trip_range: Range[int] = Range(from_order, to_order, bounds="[)")

    # Subtotal depends only on (route, from_order, to_order), so compute it
    # once for all items instead of repeating the RouteSegment scan per seat.
    base_price = Money(config.BASE_PRICE, currency=DEFAULT_CURRENCY)
    subtotal = calc_segment_range_subtotal(route, from_order, to_order)

    # Sort items by (car_number, seat_number) so two concurrent multi-seat
    # orders on overlapping seat sets always touch rows in the same order and
    # cannot deadlock on the exclusion-constraint index.
    sorted_items = sorted(items, key=lambda i: (i["car_number"], i["seat_number"]))

    resolved: list[tuple[OrderItemInput, Seat]] = []
    total = Money(currency=DEFAULT_CURRENCY)

    for item in sorted_items:
        seat = get_seat(departure.train, item["car_number"], item["seat_number"])
        resolved.append((item, seat))
        total += calc_booking_price(base_price, subtotal, seat)

    # Total is known up-front, so insert the order with its final price in a
    # single statement rather than INSERT followed by UPDATE.
    order = Order.objects.create(total_price=total)

    for item, seat in resolved:
        passenger = Passenger.objects.create(
            name=item["passenger_name"],
            passport_number=item["passenger_passport"],
            gender=item["passenger_gender"],
            birth_date=item["passenger_birth_date"],
        )

        try:
            Booking.objects.create(
                order=order,
                departure=departure,
                seat=seat,
                station_from=station_from,
                station_to=station_to,
                passenger=passenger,
                segment_range=trip_range,
            )
        except IntegrityError as e:
            if BOOKING_NO_OVERLAP_CONSTRAINT not in str(e): # pragma: no cover
                raise # should never happen if the DB schema is correct
            raise SeatUnavailableError(seat.car.number, seat.number) from e

    transaction.on_commit(lambda: DepartureGenerationCache.incr(departure.uuid))

    return order
