"""Tests for trains/services.py: search_departures and list_seats."""

from datetime import date
from decimal import Decimal

import pytest

from apps.bookings.services import create_order
from apps.stations.models import Station
from apps.trains.models import Car, Departure, Seat, Train
from apps.trains.services import list_seats, search_departures
from tests.conftest import make_order_item

# ---------------------------------------------------------------------------
# search_departures
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_unknown_station(departure: Departure) -> None:
    """Unknown station codes return an empty list, not an error."""
    result = search_departures("NOPE", "NADA", date(2026, 5, 1))
    assert result == []


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_wrong_date(
    stations: list[Station],
    seat: Seat,
    departure: Departure,
) -> None:
    """Correct stations but wrong date returns empty list."""
    result = search_departures(stations[0].code, stations[3].code, date(2099, 12, 31))
    assert result == []


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_min_price(
    stations: list[Station],
    seat: Seat,
    seat2: Seat,
    departure: Departure,
) -> None:
    """min_price reflects the cheapest free seat."""
    result = search_departures(stations[0].code, stations[3].code, date(2026, 5, 1))
    assert len(result) == 1
    # Both seats factor=1.0, full route base=100 + segments=900 = 1000
    assert result[0]["min_price"] == "$1,000.00"


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_min_price_none_when_full(
    stations: list[Station],
    car: Car,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
) -> None:
    """When all seats are booked, min_price is None."""
    for s in [seat, seat2]:
        create_order(
            departure.uuid,
            stations[0].code,
            stations[3].code,
            [make_order_item(car.number, s.number)],
        )
    result = search_departures(stations[0].code, stations[3].code, date(2026, 5, 1))
    assert result[0]["min_price"] is None
    assert result[0]["free_seat_count"] == 0


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_min_price_cheapest_seat(
    stations: list[Station],
    car: Car,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
) -> None:
    """min_price picks the cheapest among free seats when factors differ."""
    seat2.price_factor = Decimal("2.0")
    seat2.save()
    result = search_departures(stations[0].code, stations[3].code, date(2026, 5, 1))
    # seat1 factor=1.0 -> 1000, seat2 factor=2.0 -> 1900. Min = 1000
    assert result[0]["min_price"] == "$1,000.00"


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_skips_train_not_on_route(
    stations: list[Station],
    seat: Seat,
    departure: Departure,
) -> None:
    """A train whose route doesn't cover from->to is excluded."""
    # Search B->A (reverse) — our train goes A->D, so it won't match
    result = search_departures(stations[3].code, stations[0].code, date(2026, 5, 1))
    assert result == []


# ---------------------------------------------------------------------------
# list_seats
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_list_seats_invalid_station_codes(departure: Departure) -> None:
    """Unknown station codes return empty cars list."""
    result = list_seats(departure, "UNKNOWN", "ALSO")
    assert result == {"cars": []}


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_list_seats_invalid_station_code_order(
    stations: list[Station], departure: Departure
) -> None:
    """Station codes in the wrong order (to before from) also return empty cars list."""
    result = list_seats(departure, stations[-1].code, stations[0].code)
    assert result == {"cars": []}


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_list_seats_groups_by_car(
    stations: list[Station],
    train: Train,
    departure: Departure,
) -> None:
    """Multiple cars appear as separate entries in the response."""
    car1 = Car.objects.create(train=train, number=1)
    Seat.objects.create(car=car1, number=1)
    car2 = Car.objects.create(train=train, number=2)
    Seat.objects.create(car=car2, number=1)

    result = list_seats(departure, stations[0].code, stations[3].code)
    assert len(result["cars"]) == 2
    car_numbers = {c["number"] for c in result["cars"]}
    assert car_numbers == {1, 2}


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_list_seats_status_after_booking(
    stations: list[Station],
    car: Car,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
) -> None:
    """Booked seat shows status=occupied, other seat stays free."""
    create_order(
        departure.uuid,
        stations[0].code,
        stations[3].code,
        [make_order_item(car.number, seat.number)],
    )
    result = list_seats(departure, stations[0].code, stations[3].code)
    seats_out = result["cars"][0]["seats"]
    by_number = {s["number"]: s for s in seats_out}
    assert by_number[seat.number]["status"] == "occupied"
    assert by_number[seat2.number]["status"] == "free"


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_list_seats_price_reflects_car_factor(
    stations: list[Station],
    train: Train,
    departure: Departure,
) -> None:
    """A car with price_factor=1.5 produces higher seat prices."""
    expensive_car = Car.objects.create(train=train, number=10, price_factor=Decimal("1.5"))
    Seat.objects.create(car=expensive_car, number=1)

    result = list_seats(departure, stations[0].code, stations[3].code)
    car_out = next(c for c in result["cars"] if c["number"] == 10)
    # base=100 + segments=900, car_factor=1.5 -> 100 + 900*1.5 = 1450
    assert car_out["seats"][0]["price"] == "$1,450.00"
