"""Shared pytest fixtures for the railway-booking test suite.

Fixtures are composable: each test requests only the level it needs.
The dependency graph is::

    stations -> connections -> route -> train -> car -> seat / seat2
                                                    -> departure

An autouse fixture clears caches between tests to prevent cross-test leaks.
"""

from collections.abc import Generator
from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from constance.test import override_config
from django.core.cache import caches
from djmoney.money import Money

from apps.core.types import OrderItemInput
from apps.routes.models import Route, RouteSegment
from apps.stations.models import Connection, Station
from apps.trains.models import Car, Departure, Seat, Train

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


@pytest.fixture
def stations(
    station_a: Station,
    station_b: Station,
    station_c: Station,
    station_d: Station,
) -> list[Station]:
    """All four stations as a list: [A, B, C, D]."""
    return [station_a, station_b, station_c, station_d]


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
        distance_km=100,
        base_price=Money(300, "USD"),
    )


@pytest.fixture
def connection_cd(station_c: Station, station_d: Station) -> Connection:
    return Connection.objects.create(
        station_from=station_c,
        station_to=station_d,
        distance_km=100,
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
    RouteSegment.objects.create(route=r, segment=connection_ab, order=0, stop_duration=timedelta(0))
    RouteSegment.objects.create(route=r, segment=connection_bc, order=1, stop_duration=timedelta(0))
    RouteSegment.objects.create(route=r, segment=connection_cd, order=2, stop_duration=timedelta(0))
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
    return Departure.objects.create(train=train, date=date(2026, 5, 1), departure_time=time(10, 0))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_order_item(car_number: int, seat_number: int) -> OrderItemInput:
    """Build an ``OrderItemInput`` with default passenger data."""
    return OrderItemInput(
        car_number=car_number,
        seat_number=seat_number,
        passenger_name="John",
        passenger_passport="123",
        passenger_gender="male",
        passenger_birth_date="1990-01-01",
    )
