from decimal import Decimal

from django.db import transaction

from apps.core.availability import seat_is_free
from apps.core.pricing import calc_booking_price
from apps.core.timetable import find_route_orders
from apps.trains.models import Departure, Seat

from .models import Booking, Order, Passenger


class SeatUnavailableError(Exception):
    def __init__(self, seat_id: int):
        super().__init__(f"Seat {seat_id} no longer available")
        self.seat_id = seat_id


class InvalidRequestError(Exception):
    pass


@transaction.atomic
def create_order(
    departure_id: int,
    station_from_id: int,
    station_to_id: int,
    items: list[dict],
) -> Order:
    if not items:
        raise InvalidRequestError("items must not be empty")

    try:
        departure = Departure.objects.select_related("train__route").get(pk=departure_id)
    except Departure.DoesNotExist as e:
        raise InvalidRequestError("Departure not found") from e

    route = departure.train.route
    rng = find_route_orders(route, station_from_id, station_to_id)
    if not rng:
        raise InvalidRequestError("Route does not cover from→to")
    from_order, to_order = rng

    order = Order.objects.create(total_price=Decimal("0"))
    total = Decimal("0")

    for item in items:
        seat_id = item["seat_id"]
        # lock seat row to serialize concurrent bookings on same seat
        try:
            seat = Seat.objects.select_for_update().select_related("car__train").get(pk=seat_id)
        except Seat.DoesNotExist as e:
            raise InvalidRequestError(f"Seat {seat_id} not found") from e

        if seat.car.train_id != departure.train_id:
            raise InvalidRequestError(f"Seat {seat_id} does not belong to this train")

        if not seat_is_free(departure, seat_id, from_order, to_order):
            raise SeatUnavailableError(seat_id)

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
            station_from_id=station_from_id,
            station_to_id=station_to_id,
            passenger=passenger,
        )

        total += calc_booking_price(route, departure.train, seat.car, seat, from_order, to_order)

    order.total_price = total
    order.save(update_fields=["total_price"])
    return order
