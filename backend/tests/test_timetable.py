"""Tests for ``apps.core.timetable.compute_timetable``."""

from datetime import date, time, timedelta

import pytest
from djmoney.money import Money

from apps.core.timetable import compute_timetable
from apps.routes.models import Route, RouteSegment
from apps.stations.models import Connection, Station
from apps.trains.models import Departure, Train


@pytest.mark.django_db
def test_timetable_single_segment(
    station_a: Station, station_b: Station, connection_ab: Connection,
) -> None:
    """First stop has arrival_time=None; second has correct arrival based on distance/speed."""
    route = Route.objects.create(name="A-B")
    RouteSegment.objects.create(route=route, segment=connection_ab, order=0, stop_duration=timedelta(0))
    train = Train.objects.create(route=route, number="S1", name="Single", avg_speed_kmh=100)
    dep = Departure.objects.create(train=train, date=date(2026, 5, 1), departure_time=time(10, 0))

    stops = compute_timetable(dep)

    assert len(stops) == 2
    assert stops[0]["station_id"] == station_a.pk
    assert stops[0]["arrival_time"] is None
    assert stops[0]["departure_time"] == "2026-05-01T10:00"
    # 100 km / 100 km/h = 1 hour
    assert stops[1]["station_id"] == station_b.pk
    assert stops[1]["arrival_time"] == "2026-05-01T11:00"


@pytest.mark.django_db
def test_timetable_multi_segment_cumulative(
    stations: list[Station],
    connection_ab: Connection,
    connection_bc: Connection,
    connection_cd: Connection,
) -> None:
    """Travel time accumulates across segments."""
    route = Route.objects.create(name="A-D")
    RouteSegment.objects.create(route=route, segment=connection_ab, order=0, stop_duration=timedelta(0))
    RouteSegment.objects.create(route=route, segment=connection_bc, order=1, stop_duration=timedelta(0))
    RouteSegment.objects.create(route=route, segment=connection_cd, order=2, stop_duration=timedelta(0))
    train = Train.objects.create(route=route, number="M1", name="Multi", avg_speed_kmh=100)
    dep = Departure.objects.create(train=train, date=date(2026, 5, 1), departure_time=time(10, 0))

    stops = compute_timetable(dep)

    assert len(stops) == 4
    # Each segment is 100 km at 100 km/h = 1 hour
    assert stops[0]["departure_time"] == "2026-05-01T10:00"
    assert stops[1]["arrival_time"] == "2026-05-01T11:00"
    assert stops[2]["arrival_time"] == "2026-05-01T12:00"
    assert stops[3]["arrival_time"] == "2026-05-01T13:00"


@pytest.mark.django_db
def test_timetable_stop_duration_added(
    station_a: Station, station_b: Station, station_c: Station,
    connection_ab: Connection, connection_bc: Connection,
) -> None:
    """Stop duration at intermediate station delays subsequent arrival."""
    route = Route.objects.create(name="A-C-stop")
    RouteSegment.objects.create(
        route=route, segment=connection_ab, order=0, stop_duration=timedelta(0),
    )
    RouteSegment.objects.create(
        route=route, segment=connection_bc, order=1, stop_duration=timedelta(minutes=30),
    )
    train = Train.objects.create(route=route, number="SD1", name="StopDur", avg_speed_kmh=100)
    dep = Departure.objects.create(train=train, date=date(2026, 5, 1), departure_time=time(10, 0))

    stops = compute_timetable(dep)

    assert len(stops) == 3
    # A -> B: 1h, arrive 11:00
    assert stops[1]["arrival_time"] == "2026-05-01T11:00"
    # stop_duration on segment BC means B departure_time = arrival + 0 (stop_duration is on the *segment*, applied after traversal of segment 1)
    # Actually: stop_duration for segment at order=1 is applied after arriving at station_to of segment at order=0
    # Let me re-read: cursor += route_segment.stop_duration happens after traversal
    # For segment 0 (AB): travel 1h -> arrive B at 11:00, then stop_duration=0 -> depart B at 11:00
    # For segment 1 (BC): travel 1h -> arrive C at 12:00, then stop_duration=30min -> depart C at 12:30
    assert stops[1]["departure_time"] == "2026-05-01T11:00"
    assert stops[2]["arrival_time"] == "2026-05-01T12:00"
    assert stops[2]["departure_time"] == "2026-05-01T12:30"


@pytest.mark.django_db
def test_timetable_midnight_crossing(db: None) -> None:
    """Departure near midnight correctly crosses into the next day."""
    s1 = Station.objects.create(name="Night1", code="N1")
    s2 = Station.objects.create(name="Night2", code="N2")
    conn = Connection.objects.create(station_from=s1, station_to=s2, distance_km=200, base_price=Money(100, "USD"))
    route = Route.objects.create(name="Night")
    RouteSegment.objects.create(route=route, segment=conn, order=0, stop_duration=timedelta(0))
    train = Train.objects.create(route=route, number="NI1", name="Night", avg_speed_kmh=100)
    dep = Departure.objects.create(train=train, date=date(2026, 5, 1), departure_time=time(23, 30))

    stops = compute_timetable(dep)

    assert stops[0]["departure_time"] == "2026-05-01T23:30"
    # 200 km / 100 km/h = 2 hours -> 01:30 next day
    assert stops[1]["arrival_time"] == "2026-05-02T01:30"


@pytest.mark.django_db
def test_timetable_iso_format_minutes(
    station_a: Station, station_b: Station, connection_ab: Connection,
) -> None:
    """ISO strings are truncated to minutes (no seconds)."""
    route = Route.objects.create(name="A-B-iso")
    RouteSegment.objects.create(route=route, segment=connection_ab, order=0, stop_duration=timedelta(0))
    train = Train.objects.create(route=route, number="ISO1", name="Iso", avg_speed_kmh=100)
    dep = Departure.objects.create(train=train, date=date(2026, 5, 1), departure_time=time(9, 15))

    stops = compute_timetable(dep)

    # Verify no seconds in output
    for stop in stops:
        if stop["departure_time"]:
            assert stop["departure_time"].count(":") == 1
        if stop["arrival_time"]:
            assert stop["arrival_time"].count(":") == 1
