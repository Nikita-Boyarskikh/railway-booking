"""Tests for the Redis-backed cache layer (locmem in the test settings)."""

from contextlib import contextmanager
from datetime import date, timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from django.test.testcases import TestCase
from djmoney.money import Money

from apps.bookings.services import create_order
from apps.core.cache import (
    DepartureGenerationCache,
    SearchCache,
    SeatsCache,
    StationOrderMapsCache,
    StationsCache,
)
from apps.core.types import CarDict, DepartureSummary, SeatsResponse
from apps.stations.models import Station
from apps.stations.services import list_stations
from apps.trains.services import list_seats, search_departures
from tests.conftest import make_order_item

if TYPE_CHECKING:
    from collections.abc import Generator

    from apps.bookings.models import Passenger
    from apps.routes.models import Route
    from apps.stations.models import Connection
    from apps.trains.models import Car, Departure, Seat


@pytest.mark.django_db
def test_stations_cache_invalidated_on_station_change(station_a: Station) -> None:
    """Creating, modification or deleting a Station drops the cached stations:all entry.

    The invalidation signal is wrapped in ``transaction.on_commit`` so we use
    ``captureOnCommitCallbacks(execute=True)`` to drive the callbacks inside
    the test transaction (which never actually commits).
    """
    StationsCache.set(StationsCache.key(), [{"name": station_a.name, "code": station_a.code}])
    with TestCase.captureOnCommitCallbacks(execute=True):
        Station.objects.create(name="New", code="NEW")
    assert StationsCache.get() is None

    StationsCache.set(StationsCache.key(), [{"name": station_a.name, "code": station_a.code}])
    with TestCase.captureOnCommitCallbacks(execute=True):
        station_a.name = "Modified"
        station_a.save()
    assert StationsCache.get() is None

    StationsCache.set(StationsCache.key(), [{"name": station_a.name, "code": station_a.code}])
    with TestCase.captureOnCommitCallbacks(execute=True):
        Station.objects.filter(code="NEW").delete()
    assert StationsCache.get() is None


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("base_price")
def test_list_seats_cached_and_invalidated_on_booking(
    station_a: Station,
    station_b: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    """``list_seats`` hits the cache on repeat calls; a booking bumps the generation."""
    first = list_seats(departure.uuid, station_a.code, station_d.code)
    # Mutate the in-cache entry to prove the next call returns *this* value.
    cache_hit_marker = SeatsResponse(
        cars=[CarDict(number=1, car_type="common", features={"from_cache": 1}, seats=[])]
    )
    # Find the key the service stored under and overwrite it.
    gen = DepartureGenerationCache.get(departure.uuid)
    SeatsCache.set(
        SeatsCache.key(departure.uuid, station_a.code, station_d.code),
        cache_hit_marker,
    )

    second = list_seats(departure.uuid, station_a.code, station_d.code)
    assert second == cache_hit_marker, "expected cache hit on second call"
    assert second != first

    # Booking bumps the generation; the old key orphans and a fresh load runs.
    create_order(
        departure.uuid,
        station_a.code,
        station_b.code,
        [make_order_item(car.number, seat.number, passenger)],
        Money(300, "USD"),
    )
    assert DepartureGenerationCache.get(departure.uuid) > gen
    third = list_seats(departure.uuid, station_a.code, station_d.code)
    assert third != cache_hit_marker, "expected fresh data after generation bump"
    assert "cars" in third


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_cached(
    station_a: Station,
    station_d: Station,
    departure: Departure,
) -> None:
    """``search_departures`` caches its output under ``search:{from}:{to}:{date}``."""
    first = search_departures(station_a.code, station_d.code, departure.date)
    assert first
    cached = SearchCache.get(station_a.code, station_d.code, departure.date)
    assert cached == first
    # Poison the cache; subsequent call must return the poisoned value.
    SearchCache.set(
        SearchCache.key(station_a.code, station_d.code, departure.date),
        [
            DepartureSummary(
                uuid="poisoned",
                train_number="X",
                train_name="X",
                departure_time="00:00",
                arrival_time="00:00",
                free_seat_count=1,
                min_price=None,
            )
        ],
    )
    second = search_departures(station_a.code, station_d.code, departure.date)
    assert second[0]["uuid"] == "poisoned"


# ---------------------------------------------------------------------------
# DepartureGenerationCache edge cases
# ---------------------------------------------------------------------------


def test_bump_departure_generation_from_zero() -> None:
    """First bump on a fresh key returns 1."""
    assert DepartureGenerationCache.get("brand-new-uuid") == 0
    DepartureGenerationCache.incr("brand-new-uuid")
    assert DepartureGenerationCache.get("brand-new-uuid") == 1


def test_bump_departure_generation_increments() -> None:
    """Successive bumps increment the counter."""
    DepartureGenerationCache.incr("inc-uuid")
    DepartureGenerationCache.incr("inc-uuid")
    DepartureGenerationCache.incr("inc-uuid")
    assert DepartureGenerationCache.get("inc-uuid") == 3


# ---------------------------------------------------------------------------
# _get_or_set: empty list is cached (not treated as miss)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_empty_result_cached(
    station_a: Station,
    station_d: Station,
    departure: Departure,
) -> None:
    """An empty departure list is still cached (empty list != None)."""
    future = date.fromisoformat("2099-01-01")
    # Search for a date with no departures
    result = search_departures(station_a.code, station_d.code, future)
    assert result == []
    # The empty list should be in the cache
    cached = SearchCache.get(station_a.code, station_d.code, future)
    assert cached == []


# ---------------------------------------------------------------------------
# Signal-based cache invalidation — StationOrderMapsCache
# ---------------------------------------------------------------------------

_SOM_SENTINEL: tuple[dict[int, int], dict[int, int]] = ({999: 0}, {999: 1})


@pytest.mark.django_db
def test_connection_change_invalidates_station_order_maps(
    route: Route,
    connection_ab: Connection,
) -> None:
    """Saving a Connection invalidates StationOrderMapsCache for its routes."""
    StationOrderMapsCache.set(StationOrderMapsCache.key(route), _SOM_SENTINEL)
    with TestCase.captureOnCommitCallbacks(execute=True):
        connection_ab.distance_km = 999
        connection_ab.save()
    assert StationOrderMapsCache.get(route) is None


@pytest.mark.django_db
def test_route_delete_invalidates_station_order_maps(route: Route) -> None:
    """Deleting a Route invalidates its StationOrderMapsCache entry."""
    StationOrderMapsCache.set(StationOrderMapsCache.key(route), _SOM_SENTINEL)
    with TestCase.captureOnCommitCallbacks(execute=True):
        route.delete()
    assert StationOrderMapsCache.get(route) is None


@pytest.mark.django_db
def test_route_segment_change_invalidates_station_order_maps(
    route: Route,
) -> None:
    """Saving a RouteSegment invalidates StationOrderMapsCache for its route."""
    StationOrderMapsCache.set(StationOrderMapsCache.key(route), _SOM_SENTINEL)
    rs = route.route_segments.first()
    assert rs is not None
    with TestCase.captureOnCommitCallbacks(execute=True):
        rs.order = 99
        rs.save()
    assert StationOrderMapsCache.get(route) is None


# ---------------------------------------------------------------------------
# Signal-based cache invalidation — DepartureGenerationCache
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_departure_change_bumps_generation(departure: Departure) -> None:
    """Saving a Departure increments its generation counter."""
    gen_before = DepartureGenerationCache.get(departure.uuid)
    with TestCase.captureOnCommitCallbacks(execute=True):
        departure.departure_time = departure.departure_time
        departure.save()
    assert DepartureGenerationCache.get(departure.uuid) > gen_before


@pytest.mark.django_db
def test_train_change_bumps_departure_generation(
    departure: Departure,
) -> None:
    """Saving a Train bumps generation for all its departures."""
    gen_before = DepartureGenerationCache.get(departure.uuid)
    with TestCase.captureOnCommitCallbacks(execute=True):
        departure.train.name = "Renamed"
        departure.train.save()
    assert DepartureGenerationCache.get(departure.uuid) > gen_before


@pytest.mark.django_db
def test_car_change_bumps_departure_generation(
    car: Car,
    departure: Departure,
) -> None:
    """Saving a Car bumps generation for departures of the car's train."""
    gen_before = DepartureGenerationCache.get(departure.uuid)
    with TestCase.captureOnCommitCallbacks(execute=True):
        car.car_type = "luxury"
        car.save()
    assert DepartureGenerationCache.get(departure.uuid) > gen_before


@pytest.mark.django_db
def test_seat_change_bumps_departure_generation(
    seat: Seat,
    departure: Departure,
) -> None:
    """Saving a Seat bumps generation for departures of the seat's train."""
    gen_before = DepartureGenerationCache.get(departure.uuid)
    with TestCase.captureOnCommitCallbacks(execute=True):
        seat.seat_type = "vip"
        seat.save()
    assert DepartureGenerationCache.get(departure.uuid) > gen_before


# ---------------------------------------------------------------------------
# Redis unavailability — graceful degradation
# ---------------------------------------------------------------------------


@contextmanager
def cache_down() -> Generator[None]:
    with (
        patch("django.core.cache.backends.locmem.LocMemCache.get", side_effect=ConnectionError),
        patch("django.core.cache.backends.locmem.LocMemCache.set", side_effect=ConnectionError),
    ):
        yield


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_works_when_cache_down(
    station_a: Station,
    station_d: Station,
    seat: Seat,
    departure: Departure,
) -> None:
    """search_departures returns fresh data when Redis is unavailable."""
    with cache_down():
        result = search_departures(station_a.code, station_d.code, departure.date)
    assert len(result) == 1
    assert result[0]["uuid"] == str(departure.uuid)


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_list_seats_works_when_cache_down(
    station_a: Station,
    station_d: Station,
    seat: Seat,
    departure: Departure,
) -> None:
    """list_seats returns fresh data when Redis is unavailable."""
    with cache_down():
        result = list_seats(departure.uuid, station_a.code, station_d.code)
    assert "cars" in result
    assert len(result["cars"]) == 1


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_list_stations_works_when_cache_down(station_a: Station) -> None:
    """list_stations returns fresh data when Redis is unavailable."""
    with cache_down():
        result = list_stations()
    assert len(result) == 1


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_works_when_cache_down(
    station_a: Station,
    station_b: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    """create_order successfully works when Redis is unavailable."""
    with cache_down():
        item = make_order_item(car.number, seat.number, passenger)
        result = create_order(
            departure.uuid, station_a.code, station_b.code, [item], Money(300, "USD")
        )
    assert result.total_price == Money(300, "USD")


@pytest.mark.django_db
def test_cache_invalidation_does_not_raise_exception_when_cache_down(
    connection_ab: Connection, station_a: Station, departure: Departure, car: Car, seat: Seat
) -> None:
    """"""
    train = departure.train
    route = train.route
    route_segment = route.route_segments.first()
    assert route_segment

    with (
        patch("django.core.cache.backends.locmem.LocMemCache.incr", side_effect=ConnectionError),
        TestCase.captureOnCommitCallbacks(execute=True),
    ):
        route.name += "Modified"
        route.save()

        route_segment.stop_duration += timedelta(minutes=1)
        route_segment.save()

        connection_ab.distance_km += 1
        connection_ab.save()

        station_a.name += "Modified"
        station_a.save()

        departure.date += timedelta(days=1)
        departure.save()

        train.name += "Modified"
        train.save()

        car.price_factor += 1
        car.save()

        seat.price_factor += 1
        seat.save()
