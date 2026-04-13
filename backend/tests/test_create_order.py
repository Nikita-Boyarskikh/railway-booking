"""Tests for ``apps.bookings.services.create_order`` — error branches and happy paths."""

import uuid as uuid_mod
from typing import TYPE_CHECKING

import pytest
from djmoney.money import Money

from apps.bookings.exceptions import DepartureNotFoundError, SeatNotFoundError, SeatUnavailableError
from apps.bookings.models import Booking, Order, Passenger
from apps.bookings.services import create_order
from apps.routes.exceptions import InvalidStationRangeError
from apps.stations.exceptions import InvalidStationCodeError
from tests.conftest import make_order_item
from tests.factories import StationFactory

if TYPE_CHECKING:
    from apps.stations.models import Station
    from apps.trains.models import Car, Departure, Seat

# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_same_station(
    station_a: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    """Same from/to falls through to route resolution and is rejected."""
    item = make_order_item(car.number, seat.number, passenger)
    with pytest.raises(InvalidStationRangeError):
        create_order(departure.uuid, station_a.code, station_a.code, [item], Money(1000, "USD"))


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_duplicate_order(
    station_a: Station,
    station_b: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    """Booking already occupied seat was rejected."""
    item = make_order_item(car.number, seat.number, passenger)
    create_order(departure.uuid, station_a.code, station_b.code, [item], Money(300, "USD"))
    with pytest.raises(SeatUnavailableError):
        create_order(departure.uuid, station_a.code, station_b.code, [item], Money(300, "USD"))


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_with_duplicated_items(
    station_a: Station,
    station_b: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    """Booking already occupied seat was rejected."""
    item = make_order_item(car.number, seat.number, passenger)
    with pytest.raises(SeatUnavailableError):
        create_order(
            departure.uuid, station_a.code, station_b.code, [item, item], Money(600, "USD")
        )


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_unknown_departure_uuid(
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    passenger: Passenger,
) -> None:
    item = make_order_item(car.number, seat.number, passenger)
    with pytest.raises(DepartureNotFoundError):
        create_order(uuid_mod.uuid4(), station_a.code, station_d.code, [item], Money(1000, "USD"))


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_unknown_station_code(
    car: Car,
    seat: Seat,
    station_a: Station,
    departure: Departure,
    passenger: Passenger,
) -> None:
    item = make_order_item(car.number, seat.number, passenger)
    with pytest.raises(InvalidStationCodeError):
        create_order(departure.uuid, station_a.code, "UNKNOWN", [item], Money(1000, "USD"))
    with pytest.raises(InvalidStationCodeError):
        create_order(departure.uuid, "UNKNOWN", station_a.code, [item], Money(1000, "USD"))


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_station_not_on_route(
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    """Stations exist but are not part of the train's route."""
    StationFactory(code="X")
    StationFactory(code="Y")
    item = make_order_item(car.number, seat.number, passenger)
    with pytest.raises(InvalidStationRangeError):
        create_order(departure.uuid, "X", "Y", [item], Money(1000, "USD"))


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_backward_station_range(
    station_a: Station,
    station_c: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    """Booking from C to A (reverse direction) is rejected."""
    item = make_order_item(car.number, seat.number, passenger)
    with pytest.raises(InvalidStationRangeError):
        create_order(departure.uuid, station_c.code, station_a.code, [item], Money(1000, "USD"))


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_unknown_seat(
    station_a: Station,
    station_d: Station,
    departure: Departure,
    passenger: Passenger,
) -> None:
    item = make_order_item(99, 99, passenger)
    with pytest.raises(SeatNotFoundError):
        create_order(departure.uuid, station_a.code, station_d.code, [item], Money(1000, "USD"))


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_single_item(
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    item = make_order_item(car.number, seat.number, passenger)
    order = create_order(departure.uuid, station_a.code, station_d.code, [item], Money(1000, "USD"))

    assert Order.objects.count() == 1
    assert Booking.objects.count() == 1
    assert Passenger.objects.count() == 2
    assert order.total_price == Money("1000.00", "USD")


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_multiple_items(
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    """Two seats in one order — total_price is sum of both."""
    items = [
        make_order_item(car.number, seat.number, passenger),
        make_order_item(car.number, seat2.number, passenger),
    ]
    order = create_order(departure.uuid, station_a.code, station_d.code, items, Money(2000, "USD"))

    assert order.bookings.count() == 2
    assert Passenger.objects.count() == 3
    # Both seats have price_factor=1.0, so each booking = 1000
    assert order.total_price == Money("2000.00", "USD")


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_partial_route(
    station_a: Station,
    station_b: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    """Booking for a sub-segment (A->B) prices only that segment."""
    item = make_order_item(car.number, seat.number, passenger)
    order = create_order(departure.uuid, station_a.code, station_b.code, [item], Money(300, "USD"))
    # segment AB base_price=200, + BASE_PRICE=100
    assert order.total_price == Money("300.00", "USD")


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_rolls_back_on_conflict(
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    """If second item fails, entire order is rolled back (atomic)."""
    # Book seat1 for A->D first
    create_order(
        departure.uuid,
        station_a.code,
        station_d.code,
        [make_order_item(car.number, seat.number, passenger)],
        Money(1000, "USD"),
    )

    # Now try to book seat2 + seat1(conflict) in one order
    items = [
        make_order_item(car.number, seat2.number, passenger),
        make_order_item(car.number, seat.number, passenger),  # already booked
    ]
    with pytest.raises(SeatUnavailableError):
        create_order(departure.uuid, station_a.code, station_d.code, items, Money(2000, "USD"))

    # seat2 booking should have been rolled back
    assert Booking.objects.filter(seat=seat2).count() == 0
    assert Order.objects.count() == 1  # only the first order
