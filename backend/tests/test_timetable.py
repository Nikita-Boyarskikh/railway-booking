"""Tests for ``apps.core.timetable.compute_timetable``."""

from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING

import pytest

from apps.core.timetable import compute_timetable
from tests.factories import (
    ConnectionFactory,
    DepartureFactory,
    RouteFactory,
    RouteSegmentFactory,
    StationFactory,
    TrainFactory,
)

if TYPE_CHECKING:
    from apps.stations.models import Connection, Station

_DATE = date.fromisoformat("2026-05-01")
_TIME = time.fromisoformat("10:00")


def _fmt(dt: datetime) -> str:
    return dt.isoformat(timespec="minutes")


@pytest.mark.django_db
def test_timetable_single_segment(
    station_a: Station,
    station_b: Station,
    connection_ab: Connection,
) -> None:
    """First stop has arrival_time=None; second has correct arrival based on distance/speed."""
    route = RouteFactory(name="A-B")
    RouteSegmentFactory(route=route, connection=connection_ab, order=0, stop_duration=timedelta(0))
    train = TrainFactory(route=route, avg_speed_kmh=100)
    dep = DepartureFactory(train=train, date=_DATE, departure_time=_TIME)

    stops = compute_timetable(dep)

    depart_at = datetime.combine(_DATE, _TIME)
    assert len(stops) == 2
    assert stops[0]["station_id"] == station_a.pk
    assert stops[0]["arrival_time"] is None
    assert stops[0]["departure_time"] == _fmt(depart_at)
    # 100 km / 100 km/h = 1 hour
    assert stops[1]["station_id"] == station_b.pk
    assert stops[1]["arrival_time"] == _fmt(depart_at + timedelta(hours=1))


@pytest.mark.django_db
def test_timetable_multi_segment_cumulative(
    connection_ab: Connection,
    connection_bc: Connection,
    connection_cd: Connection,
) -> None:
    """Travel time accumulates across segments."""
    route = RouteFactory(name="A-D")
    RouteSegmentFactory(route=route, connection=connection_ab, order=0, stop_duration=timedelta(0))
    RouteSegmentFactory(route=route, connection=connection_bc, order=1, stop_duration=timedelta(0))
    RouteSegmentFactory(route=route, connection=connection_cd, order=2, stop_duration=timedelta(0))
    train = TrainFactory(route=route, avg_speed_kmh=100)
    dep = DepartureFactory(train=train, date=_DATE, departure_time=_TIME)

    stops = compute_timetable(dep)

    depart_at = datetime.combine(_DATE, _TIME)
    assert len(stops) == 4
    # AB=100km, BC=200km, CD=300km at 100 km/h => 1h, 2h, 3h cumulative = 1h, 3h, 6h
    assert stops[0]["departure_time"] == _fmt(depart_at)
    assert stops[1]["arrival_time"] == _fmt(depart_at + timedelta(hours=1))
    assert stops[2]["arrival_time"] == _fmt(depart_at + timedelta(hours=3))
    assert stops[3]["arrival_time"] == _fmt(depart_at + timedelta(hours=6))


@pytest.mark.django_db
def test_timetable_stop_duration_added(
    station_a: Station,
    station_b: Station,
    station_c: Station,
    connection_ab: Connection,
    connection_bc: Connection,
) -> None:
    """Stop duration at intermediate station delays subsequent arrival."""
    route = RouteFactory(name="A-C-stop")
    RouteSegmentFactory(
        route=route,
        connection=connection_ab,
        order=0,
        stop_duration=timedelta(minutes=10),
    )
    RouteSegmentFactory(
        route=route,
        connection=connection_bc,
        order=1,
        stop_duration=timedelta(minutes=30),
    )
    train = TrainFactory(route=route, avg_speed_kmh=100)
    dep = DepartureFactory(train=train, date=_DATE, departure_time=_TIME)

    stops = compute_timetable(dep)

    depart_at = datetime.combine(_DATE, _TIME)
    assert len(stops) == 3
    # A→B: 100km/100kmh = 1h → arrive B at +1h
    assert stops[1]["arrival_time"] == _fmt(depart_at + timedelta(hours=1))
    # stop_duration=10min at B → depart B at +1h10m
    assert stops[1]["departure_time"] == _fmt(depart_at + timedelta(hours=1, minutes=10))
    # B→C: 200km/100kmh = 2h → arrive C at +3h10m
    assert stops[2]["arrival_time"] == _fmt(depart_at + timedelta(hours=3, minutes=10))
    # stop_duration=30min at C → depart C at +3h40m
    assert stops[2]["departure_time"] == _fmt(depart_at + timedelta(hours=3, minutes=40))


@pytest.mark.django_db
def test_timetable_midnight_crossing() -> None:
    """Departure near midnight correctly crosses into the next day."""
    s1 = StationFactory(name="Night1", code="N1")
    s2 = StationFactory(name="Night2", code="N2")
    conn = ConnectionFactory(station_from=s1, station_to=s2, distance_km=200)
    route = RouteFactory(name="Night")
    RouteSegmentFactory(route=route, connection=conn, order=0, stop_duration=timedelta(0))
    train = TrainFactory(route=route, avg_speed_kmh=100)
    dep = DepartureFactory(train=train, date=_DATE, departure_time=time.fromisoformat("23:30"))

    stops = compute_timetable(dep)

    depart_at = datetime.combine(_DATE, time.fromisoformat("23:30"))
    assert stops[0]["departure_time"] == _fmt(depart_at)
    # 200 km / 100 km/h = 2 hours → 01:30 next day
    assert stops[1]["arrival_time"] == _fmt(depart_at + timedelta(hours=2))
