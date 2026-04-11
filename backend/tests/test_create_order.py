"""Tests for ``apps.bookings.services.create_order`` — error branches and happy paths."""

import uuid as uuid_mod

import pytest
from moneyed import Money

from apps.bookings.models import Booking, Order, Passenger
from apps.bookings.services import InvalidRequestError, SeatUnavailableError, create_order
from apps.stations.models import Station
from apps.trains.models import Car, Departure, Seat
from tests.conftest import make_order_item

# ---------------------------------------------------------------------------
# Validation errors (InvalidRequestError → 400 in the view)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_same_station(
    stations: list[Station], car: Car, seat: Seat, departure: Departure,
) -> None:
    """Same from/to falls through to route resolution and is rejected."""
    item = make_order_item(car.number, seat.number)
    with pytest.raises(InvalidRequestError, match="does not cover"):
        create_order(departure.uuid, stations[0].code, stations[0].code, [item])


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_unknown_departure_uuid(
    stations: list[Station], car: Car, seat: Seat,
) -> None:
    item = make_order_item(car.number, seat.number)
    with pytest.raises(InvalidRequestError, match="not found"):
        create_order(uuid_mod.uuid4(), stations[0].code, stations[3].code, [item])


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_invalid_uuid_format(
    stations: list[Station], car: Car, seat: Seat,
) -> None:
    item = make_order_item(car.number, seat.number)
    with pytest.raises(InvalidRequestError, match="not found"):
        create_order("not-a-uuid", stations[0].code, stations[3].code, [item])


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_unknown_station_code(
    car: Car, seat: Seat, departure: Departure,
) -> None:
    item = make_order_item(car.number, seat.number)
    with pytest.raises(InvalidRequestError, match="Unknown station"):
        create_order(departure.uuid, "NOPE", "NADA", [item])


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_station_not_on_route(
    car: Car, seat: Seat, departure: Departure, db: None,
) -> None:
    """Stations exist but are not part of the train's route."""
    Station.objects.create(name="X", code="X")
    Station.objects.create(name="Y", code="Y")
    item = make_order_item(car.number, seat.number)
    with pytest.raises(InvalidRequestError, match="does not cover"):
        create_order(departure.uuid, "X", "Y", [item])


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_backward_station_range(
    stations: list[Station], car: Car, seat: Seat, departure: Departure,
) -> None:
    """Booking from C to A (reverse direction) is rejected."""
    item = make_order_item(car.number, seat.number)
    with pytest.raises(InvalidRequestError):
        create_order(departure.uuid, stations[2].code, stations[0].code, [item])


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_unknown_seat(
    stations: list[Station], departure: Departure,
) -> None:
    item = make_order_item(car_number=99, seat_number=99)
    with pytest.raises(InvalidRequestError, match="not found"):
        create_order(departure.uuid, stations[0].code, stations[3].code, [item])


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_single_item(
    stations: list[Station], car: Car, seat: Seat, departure: Departure,
) -> None:
    item = make_order_item(car.number, seat.number)
    order = create_order(departure.uuid, stations[0].code, stations[3].code, [item])

    assert Order.objects.count() == 1
    assert Booking.objects.count() == 1
    assert Passenger.objects.count() == 1
    assert order.total_price == Money("1000.00", "USD")


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_multiple_items(
    stations: list[Station], car: Car, seat: Seat, seat2: Seat, departure: Departure,
) -> None:
    """Two seats in one order — total_price is sum of both."""
    items = [
        make_order_item(car.number, seat.number),
        make_order_item(car.number, seat2.number),
    ]
    order = create_order(departure.uuid, stations[0].code, stations[3].code, items)

    assert order.bookings.count() == 2
    assert Passenger.objects.count() == 2
    # Both seats have price_factor=1.0, so each booking = 1000
    assert order.total_price == Money("2000.00", "USD")


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_partial_route(
    stations: list[Station], car: Car, seat: Seat, departure: Departure,
) -> None:
    """Booking for a sub-segment (A->B) prices only that segment."""
    item = make_order_item(car.number, seat.number)
    order = create_order(departure.uuid, stations[0].code, stations[1].code, [item])
    # segment AB base_price=200, + BASE_PRICE=100
    assert order.total_price == Money("300.00", "USD")


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_rolls_back_on_conflict(
    stations: list[Station], car: Car, seat: Seat, seat2: Seat, departure: Departure,
) -> None:
    """If second item fails, entire order is rolled back (atomic)."""
    # Book seat1 for A->D first
    create_order(
        departure.uuid, stations[0].code, stations[3].code,
        [make_order_item(car.number, seat.number)],
    )

    # Now try to book seat2 + seat1(conflict) in one order
    items = [
        make_order_item(car.number, seat2.number),
        make_order_item(car.number, seat.number),  # already booked
    ]
    with pytest.raises(SeatUnavailableError):
        create_order(departure.uuid, stations[0].code, stations[3].code, items)

    # seat2 booking should have been rolled back
    assert Booking.objects.filter(seat=seat2).count() == 0
    assert Order.objects.count() == 1  # only the first order
