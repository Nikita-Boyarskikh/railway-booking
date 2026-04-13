"""Tests for search_departures."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from djmoney.money import Money

from apps.bookings.services import create_order
from apps.stations.exceptions import InvalidStationCodeError
from apps.trains.models import Car, Departure, Seat, Train
from apps.trains.services import search_departures
from tests.conftest import make_order_item

if TYPE_CHECKING:
    from apps.bookings.models import Passenger
    from apps.stations.models import Station


@pytest.mark.django_db
def test_search_departures_unknown_station(departure: Departure, station_a: Station) -> None:
    """Unknown station codes raise an :class:`InvalidStationCodeError`."""
    with pytest.raises(InvalidStationCodeError):
        search_departures("UNKNOWN", station_a.code, departure.date)
    with pytest.raises(InvalidStationCodeError):
        search_departures(station_a.code, "UNKNOWN", departure.date)


@pytest.mark.django_db
def test_search_departures_wrong_date(
    station_a: Station,
    station_d: Station,
    seat: Seat,
    departure: Departure,
) -> None:
    """Correct stations but wrong date returns empty list."""
    result = search_departures(station_a.code, station_d.code, date.fromisoformat("2099-12-31"))
    assert result == []


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_one(
    station_a: Station,
    station_d: Station,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
) -> None:
    depart_at = datetime.combine(departure.date, departure.departure_time)
    result = search_departures(station_a.code, station_d.code, departure.date)
    assert result == [
        {
            "uuid": str(departure.uuid),
            "train_name": departure.train.name,
            "train_number": departure.train.number,
            "departure_time": depart_at.isoformat(timespec="minutes"),
            # 100km (A-B) + 200km (B-C) + 300km (C-D) = 600km / 100kmph = 6h
            "arrival_time": (depart_at + timedelta(hours=6)).isoformat(timespec="minutes"),
            # Both seats factor=1.0, full route base=100 + segments=900 = 1000,
            "min_price": "$1,000.00",
            "free_seat_count": 2,
        }
    ]


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_many(
    station_a: Station,
    station_d: Station,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
) -> None:
    speed_train = Train.objects.create(
        route=departure.train.route,
        number="XXX",
        name="Speed Train",
        avg_speed_kmh=200,
        price_factor=2,
    )
    speed_train_car = Car.objects.create(train=speed_train, number=1)
    Seat.objects.create(car=speed_train_car, number=1)
    speed_departure1 = Departure.objects.create(
        train=speed_train,
        date=departure.date,
        departure_time=time(departure.departure_time.hour + 1, departure.departure_time.minute),
    )
    Departure.objects.create(
        train=speed_train,
        date=departure.date,
        departure_time=time(departure.departure_time.hour + 2, departure.departure_time.minute),
    )

    result = search_departures(station_a.code, station_d.code, departure.date)

    assert len(result) == 3
    speed_depart_at1 = datetime.combine(speed_departure1.date, speed_departure1.departure_time)
    assert result[1] == {
        "uuid": str(speed_departure1.uuid),
        "train_name": speed_train.name,
        "train_number": speed_train.number,
        "departure_time": speed_depart_at1.isoformat(timespec="minutes"),
        "arrival_time": (speed_depart_at1 + timedelta(hours=3)).isoformat(timespec="minutes"),
        "min_price": "$1,900.00",
        "free_seat_count": 1,
    }


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_min_price_none_when_full(
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    """When all seats are booked, min_price is None."""
    create_order(
        departure.uuid,
        station_a.code,
        station_d.code,
        [make_order_item(car.number, s.number, passenger) for s in [seat, seat2]],
        Money(2000, "USD"),
    )
    result = search_departures(station_a.code, station_d.code, departure.date)
    assert result[0]["min_price"] is None
    assert result[0]["free_seat_count"] == 0


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_min_price_cheapest_seat(
    station_a: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
) -> None:
    """min_price picks the cheapest among free seats when factors differ."""
    seat2.price_factor = Decimal("2.0")
    seat2.save()
    result = search_departures(station_a.code, station_d.code, departure.date)
    # seat1 factor=1.0 -> 1000, seat2 factor=2.0 -> 1900. Min = 1000
    assert result[0]["min_price"] == "$1,000.00"
    assert result[0]["free_seat_count"] == 2


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_skips_train_not_on_route(
    station_a: Station,
    station_b: Station,
    seat: Seat,
    departure: Departure,
) -> None:
    """A train whose route doesn't cover from->to is excluded."""
    # Search B->A (reverse) — our train goes A->D, so it won't match
    result = search_departures(station_b.code, station_a.code, departure.date)
    assert result == []


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_reverse_direction_on_route(
    station_b: Station,
    station_c: Station,
    seat: Seat,
    departure: Departure,
) -> None:
    """C→B is reverse on the A→B→C→D route — should return empty list."""
    result = search_departures(station_c.code, station_b.code, departure.date)
    assert result == []
