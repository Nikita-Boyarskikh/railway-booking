"""Service layer for the bookings app: order creation and validation."""

import uuid as uuid_mod

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from djmoney.money import Money

from apps.core.availability import resolve_station_range, seat_is_free
from apps.core.cache import bump_departure_generation
from apps.core.pricing import calc_booking_price, calc_segment_range_subtotal
from apps.core.types import OrderItemInput
from apps.stations.models import Station
from apps.trains.models import Departure, Seat
from config.settings import DEFAULT_CURRENCY

from .models import Booking, Order, Passenger


class SeatUnavailableError(Exception):
    """Raised when a requested seat was taken between validation and commit."""

    def __init__(self, car_number: int, seat_number: int):
        super().__init__(_("Seat car={car_number} seat={seat_number} no longer available").format(
            seat_number=seat_number,
            car_number=car_number,
        ))
        self.car_number = car_number
        self.seat_number = seat_number


class InvalidRequestError(Exception):
    """Raised for business-logic errors during order creation (maps to 400)."""


@transaction.atomic
def create_order(
    departure_uuid: str | uuid_mod.UUID,
    station_from_code: str,
    station_to_code: str,
    items: list[OrderItemInput],
) -> Order:
    """Create an :class:`Order` with one :class:`Booking` per ``item``.

    Runs inside a single transaction and takes a row-level lock on each
    selected :class:`~apps.trains.models.Seat` to prevent double-booking.

    Input validation (empty items, same station, field types) is expected
    to be handled by the serializer layer before calling this function.

    Raises:
        InvalidRequestError: On unknown references or route mismatch.
        SeatUnavailableError: If a requested seat is already booked for the range.
    """
    try:
        departure = Departure.objects.select_related("train__route").get(uuid=departure_uuid)
    except (Departure.DoesNotExist, ValidationError) as e:
        raise InvalidRequestError(_("Departure not found")) from e

    stations = {
        s.code: s for s in Station.objects.filter(code__in=[station_from_code, station_to_code])
    }
    station_from = stations.get(station_from_code)
    station_to = stations.get(station_to_code)
    if not station_from or not station_to:
        raise InvalidRequestError(_("Unknown station code"))

    route = departure.train.route
    rng = resolve_station_range(route, station_from.id, station_to.id)
    if not rng:
        raise InvalidRequestError(
            _("Route does not cover the requested station_from → station_to segment")
        )
    from_order, to_order = rng

    order = Order.objects.create()
    total = Money(currency=DEFAULT_CURRENCY)

    for item in items:
        car_number = item["car_number"]
        seat_number = item["seat_number"]

        try:
            seat = (
                Seat.objects.select_for_update()
                .select_related("car__train")
                .get(
                    car__train=departure.train,
                    car__number=car_number,
                    number=seat_number,
                )
            )
        except Seat.DoesNotExist as e:
            raise InvalidRequestError(
                _("Seat car={car_number} seat={seat_number} not found on this train").format(
                    car_number=car_number,
                    seat_number=seat_number,
                )
            ) from e

        if not seat_is_free(departure, seat.pk, from_order, to_order):
            raise SeatUnavailableError(car_number, seat_number)

        passenger = Passenger.objects.create(
            name=item["passenger_name"],
            passport_number=item["passenger_passport"],
            gender=item["passenger_gender"],
            birth_date=item["passenger_birth_date"],
        )

        Booking.objects.create(
            order=order,
            departure=departure,
            seat=seat,
            station_from=station_from,
            station_to=station_to,
            passenger=passenger,
        )

        subtotal = calc_segment_range_subtotal(route, from_order, to_order)
        total += calc_booking_price(subtotal, seat)

    order.total_price = total
    order.save(update_fields=["total_price"])

    dep_uuid = str(departure.uuid)
    transaction.on_commit(lambda: bump_departure_generation(dep_uuid))

    return order
