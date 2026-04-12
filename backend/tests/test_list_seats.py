"""Tests for list_seats."""

from decimal import Decimal

import pytest

from apps.bookings.models import Passenger
from apps.bookings.services import create_order
from apps.core.types import SeatStatus
from apps.routes.exceptions import InvalidStationRangeError
from apps.stations.exceptions import InvalidStationCodeError
from apps.stations.models import Station
from apps.trains.models import Car, Departure, Seat, Train
from apps.trains.services import list_seats
from tests.conftest import make_order_item


@pytest.mark.django_db
def test_list_seats_invalid_station_codes(departure: Departure, station_a: Station) -> None:
    """Unknown station codes raise an :class:`InvalidStationCodeError`."""
    with pytest.raises(InvalidStationCodeError):
        list_seats(departure.uuid, "UNKNOWN", station_a.code)
    with pytest.raises(InvalidStationCodeError):
        list_seats(departure.uuid, station_a.code, "UNKNOWN")


@pytest.mark.django_db
def test_list_seats_invalid_station_code_order(
    station_a: Station, station_d: Station, departure: Departure
) -> None:
    """Station codes in the wrong order raise an :class:`InvalidStationRangeError`."""
    with pytest.raises(InvalidStationRangeError):
        list_seats(departure.uuid, station_d.code, station_a.code)


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_list_seats_groups_by_car(
    station_a: Station,
    station_d: Station,
    train: Train,
    departure: Departure,
) -> None:
    """Multiple cars appear as separate entries in the response."""
    car1 = Car.objects.create(train=train, number=1)
    Seat.objects.create(car=car1, number=1)
    car2 = Car.objects.create(train=train, number=2)
    Seat.objects.create(car=car2, number=1)
    Seat.objects.create(car=car2, number=2)

    result = list_seats(departure.uuid, station_a.code, station_d.code)
    assert len(result["cars"]) == 2
    car_to_seats_count = {c["number"]: len(c["seats"]) for c in result["cars"]}
    assert car_to_seats_count == {1: 1, 2: 2}


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_list_seats_status_after_booking(
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    """Booked seat shows status=occupied, other seat stays free."""
    create_order(
        departure.uuid,
        station_a.code,
        station_d.code,
        [make_order_item(car.number, seat.number, passenger)],
    )
    result = list_seats(departure.uuid, station_a.code, station_d.code)
    seats_out = result["cars"][0]["seats"]
    status_by_number = {s["number"]: s["status"] for s in seats_out}
    assert status_by_number[seat.number] == SeatStatus.OCCUPIED
    assert status_by_number[seat2.number] == SeatStatus.FREE


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_list_seats_price_reflects_car_factor(
    station_a: Station,
    station_d: Station,
    train: Train,
    departure: Departure,
) -> None:
    """A car with price_factor=1.5 produces higher seat prices."""
    expensive_car = Car.objects.create(train=train, number=10, price_factor=Decimal("1.5"))
    Seat.objects.create(car=expensive_car, number=1)

    result = list_seats(departure.uuid, station_a.code, station_d.code)
    car_out = next(c for c in result["cars"] if c["number"] == 10)
    # base=100 + segments=900, car_factor=1.5 -> 100 + 900*1.5 = 1450
    assert car_out["seats"][0]["price"] == "$1,450.00"
