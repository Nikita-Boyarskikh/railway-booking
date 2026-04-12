"""Shared pytest fixtures for the railway-booking test suite.

Fixtures are composable: each test requests only the level it needs.
The dependency graph is::

    stations -> connections -> route -> train -> car -> seat / seat2
                                                    -> departure

An autouse fixture clears caches between tests to prevent cross-test leaks.
"""

from datetime import date, time, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from constance.test import override_config
from django.core.cache import caches
from djmoney.money import Money

from apps.bookings.models import Booking, Order, Passenger
from apps.core.availability import make_segment_range
from apps.core.types import OrderItemInput, PassengerDict
from apps.routes.models import Route, RouteSegment
from apps.routes.services import resolve_station_range
from apps.stations.models import Connection, Station
from apps.trains.models import Car, Departure, Seat, Train

if TYPE_CHECKING:
    from collections.abc import Generator

# ---------------------------------------------------------------------------
# Autouse: prevent process-level cache leaks between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_caches() -> Generator[None]:
    """Clear Django caches between tests."""
    for cache in caches.all():
        cache.clear()
    yield
    for cache in caches.all():
        cache.clear()


# ---------------------------------------------------------------------------
# Constance config
# ---------------------------------------------------------------------------


@pytest.fixture
def base_price() -> Generator[None]:
    """Set ``config.BASE_PRICE`` to 100 for the duration of a test."""
    with override_config(BASE_PRICE=Decimal(100)):
        yield


# ---------------------------------------------------------------------------
# Stations
# ---------------------------------------------------------------------------


@pytest.fixture
def station_a(db: None) -> Station:
    return Station.objects.create(name="A", code="A")


@pytest.fixture
def station_b(db: None) -> Station:
    return Station.objects.create(name="B", code="B")


@pytest.fixture
def station_c(db: None) -> Station:
    return Station.objects.create(name="C", code="C")


@pytest.fixture
def station_d(db: None) -> Station:
    return Station.objects.create(name="D", code="D")


# ---------------------------------------------------------------------------
# Connections (segments between adjacent stations)
# ---------------------------------------------------------------------------


@pytest.fixture
def connection_ab(station_a: Station, station_b: Station) -> Connection:
    return Connection.objects.create(
        station_from=station_a,
        station_to=station_b,
        distance_km=100,
        base_price=Money(200, "USD"),
    )


@pytest.fixture
def connection_bc(station_b: Station, station_c: Station) -> Connection:
    return Connection.objects.create(
        station_from=station_b,
        station_to=station_c,
        distance_km=200,
        base_price=Money(300, "USD"),
    )


@pytest.fixture
def connection_cd(station_c: Station, station_d: Station) -> Connection:
    return Connection.objects.create(
        station_from=station_c,
        station_to=station_d,
        distance_km=300,
        base_price=Money(400, "USD"),
    )


# ---------------------------------------------------------------------------
# Route  (A -> B -> C -> D)
# ---------------------------------------------------------------------------


@pytest.fixture
def route(
    connection_ab: Connection,
    connection_bc: Connection,
    connection_cd: Connection,
) -> Route:
    r = Route.objects.create(name="A-D")
    RouteSegment.objects.create(
        route=r, connection=connection_ab, order=0, stop_duration=timedelta(0)
    )
    RouteSegment.objects.create(
        route=r, connection=connection_bc, order=1, stop_duration=timedelta(0)
    )
    RouteSegment.objects.create(
        route=r, connection=connection_cd, order=2, stop_duration=timedelta(0)
    )
    return r


# ---------------------------------------------------------------------------
# Train / Car / Seats
# ---------------------------------------------------------------------------


@pytest.fixture
def train(route: Route) -> Train:
    return Train.objects.create(route=route, number="100", name="T", avg_speed_kmh=100)


@pytest.fixture
def car(train: Train) -> Car:
    return Car.objects.create(train=train, number=1)


@pytest.fixture
def seat(car: Car) -> Seat:
    return Seat.objects.create(car=car, number=1)


@pytest.fixture
def seat2(car: Car) -> Seat:
    return Seat.objects.create(car=car, number=2)


# ---------------------------------------------------------------------------
# Departure
# ---------------------------------------------------------------------------


@pytest.fixture
def departure(train: Train) -> Departure:
    return Departure.objects.create(
        train=train,
        date=date.fromisoformat("2026-05-01"),
        departure_time=time.fromisoformat("10:00"),
    )


@pytest.fixture
def backward_departure(route: Route, station_b: Station, station_a: Station) -> Departure:
    backward_route = Route.objects.create(name="B-A")
    connection_ba = Connection.objects.create(
        station_from=station_b,
        station_to=station_a,
        distance_km=100,
        base_price=Money(400, "USD"),
    )
    RouteSegment.objects.create(
        route=backward_route, connection=connection_ba, order=0, stop_duration=timedelta(0)
    )
    backward_train = Train.objects.create(
        route=backward_route, number="200", name="Backward", avg_speed_kmh=100
    )
    return Departure.objects.create(
        train=backward_train,
        date=date.fromisoformat("2026-05-01"),
        departure_time=time.fromisoformat("12:00"),
    )


# ---------------------------------------------------------------------------
# Passengers
# ---------------------------------------------------------------------------


@pytest.fixture
def passenger(db: None) -> Passenger:
    return Passenger.objects.create(
        name="John Johns",
        gender="male",
        passport_number="1234567890",
        birth_date=date(1990, 1, 1),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_order_item(car_number: int, seat_number: int, passenger: Passenger) -> OrderItemInput:
    """Build an ``OrderItemInput`` with default passenger data."""
    return OrderItemInput(
        car_number=car_number,
        seat_number=seat_number,
        passenger=PassengerDict(
            name=passenger.name,
            passport_number=passenger.passport_number,
            gender=passenger.gender,
            birth_date=passenger.birth_date,
        ),
    )


def create_booking(
    departure: Departure,
    seat: Seat,
    station_from: Station,
    station_to: Station,
    passenger: Passenger,
) -> None:
    """Create a minimal Booking for testing (bypasses service layer)."""
    order = Order.objects.create()
    from_order, to_order = resolve_station_range(
        departure.train.route, station_from.pk, station_to.pk
    )
    route_segment_exists = from_order is not None and to_order is not None
    assert route_segment_exists, "test fixture requested an impossible route segment"
    Booking.objects.create(
        order=order,
        departure=departure,
        seat=seat,
        station_from=station_from,
        station_to=station_to,
        passenger=passenger,
        segment_range=make_segment_range(from_order, to_order),
    )
