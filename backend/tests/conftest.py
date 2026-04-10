from datetime import date, time, timedelta
from decimal import Decimal
from typing import TypedDict

import pytest
from constance import config

from apps.routes.models import Route, RouteSegment
from apps.stations.models import Connection, Station
from apps.trains.models import Car, Departure, Seat, Train


class TypeTestData(TypedDict):
    stations: list[Station]
    route: Route
    train: Train
    car: Car
    seat: Seat
    seat2: Seat
    departure: Departure


@pytest.fixture
def test_data(db: None) -> TypeTestData:
    config.BASE_PRICE = Decimal(100)

    station_a = Station.objects.create(name="A", code="A")
    station_b = Station.objects.create(name="B", code="B")
    station_c = Station.objects.create(name="C", code="C")
    station_d = Station.objects.create(name="D", code="D")

    segment_ab = Connection.objects.create(station_from=station_a, station_to=station_b, distance_km=100, base_price=200)
    segment_bc = Connection.objects.create(station_from=station_b, station_to=station_c, distance_km=100, base_price=300)
    segment_cd = Connection.objects.create(station_from=station_c, station_to=station_d, distance_km=100, base_price=400)

    route = Route.objects.create(name="A-D")
    RouteSegment.objects.create(route=route, segment=segment_ab, order=0, stop_duration=timedelta(0))
    RouteSegment.objects.create(route=route, segment=segment_bc, order=1, stop_duration=timedelta(0))
    RouteSegment.objects.create(route=route, segment=segment_cd, order=2, stop_duration=timedelta(0))

    train = Train.objects.create(
        route=route,
        number="100",
        name="T",
        avg_speed_kmh=100,
    )
    car = Car.objects.create(train=train, number=1)
    seat = Seat.objects.create(car=car, number=1)
    seat2 = Seat.objects.create(car=car, number=2)

    departure = Departure.objects.create(
        train=train,
        date=date(2026, 5, 1),
        departure_time=time(10, 0),
    )

    return TypeTestData(
        stations=[station_a, station_b, station_c, station_d],
        route=route,
        train=train,
        car=car,
        seat=seat,
        seat2=seat2,
        departure=departure,
    )
