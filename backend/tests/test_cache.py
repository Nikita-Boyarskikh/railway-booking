"""Tests for the Redis-backed cache layer (locmem in the test settings)."""

from datetime import date

import pytest
from django.test.testcases import TestCase

from apps.bookings.services import create_order
from apps.core.cache import (
    _SEATS_TMPL,
    STATIONS_KEY,
    bump_departure_generation,
    get_departure_generation,
    redis_cache,
)
from apps.core.types import CarDict, DepartureSummary, SeatsResponse
from apps.stations.models import Station
from apps.trains.models import Car, Departure, Seat
from apps.trains.services import list_seats, search_departures
from tests.conftest import make_order_item


@pytest.mark.django_db
def test_stations_cache_invalidated_on_station_change(station_a: Station) -> None:
    """Creating, modification or deleting a Station drops the cached stations:all entry.

    The invalidation signal is wrapped in ``transaction.on_commit`` so we use
    ``captureOnCommitCallbacks(execute=True)`` to drive the callbacks inside
    the test transaction (which never actually commits).
    """
    redis_cache.set(STATIONS_KEY, [{"name": "stale", "code": "STL"}], timeout=300)
    with TestCase.captureOnCommitCallbacks(execute=True):
        Station.objects.create(name="New", code="NEW")
    assert redis_cache.get(STATIONS_KEY) is None

    redis_cache.set(STATIONS_KEY, [{"name": "stale", "code": "STL2"}], timeout=300)
    with TestCase.captureOnCommitCallbacks(execute=True):
        station_a.name = "Modified"
        station_a.save()
    assert redis_cache.get(STATIONS_KEY) is None

    redis_cache.set(STATIONS_KEY, [{"name": "stale2", "code": "STL1"}], timeout=300)
    with TestCase.captureOnCommitCallbacks(execute=True):
        Station.objects.filter(code="NEW").delete()
    assert redis_cache.get(STATIONS_KEY) is None


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("base_price")
def test_list_seats_cached_and_invalidated_on_booking(
    stations: list[Station],
    car: Car,
    seat: Seat,
    departure: Departure,
) -> None:
    """``list_seats`` hits the cache on repeat calls; a booking bumps the generation."""
    first = list_seats(departure, stations[0].code, stations[3].code)
    # Mutate the in-cache entry to prove the next call returns *this* value.
    cache_hit_marker = SeatsResponse(
        cars=[CarDict(number=1, car_type="common", features={"from_cache": 1}, seats=[])]
    )
    # Find the key the service stored under and overwrite it.
    gen = get_departure_generation(str(departure.uuid))
    key = _SEATS_TMPL.format(uuid=departure.uuid, from_=stations[0].code, to=stations[3].code, gen=gen)
    redis_cache.set(key, cache_hit_marker, timeout=60)

    second = list_seats(departure, stations[0].code, stations[3].code)
    assert second == cache_hit_marker, "expected cache hit on second call"
    assert second != first

    # Booking bumps the generation; the old key orphans and a fresh load runs.
    create_order(
        departure.uuid,
        stations[0].code,
        stations[1].code,
        [make_order_item(car.number, seat.number)],
    )
    assert get_departure_generation(str(departure.uuid)) > gen
    third = list_seats(departure, stations[0].code, stations[3].code)
    assert third != cache_hit_marker, "expected fresh data after generation bump"
    assert "cars" in third


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_cached(stations: list[Station], departure: Departure) -> None:
    """``search_departures`` caches its output under ``search:{from}:{to}:{date}``."""
    s = stations

    first = search_departures(s[0].code, s[3].code, date(2026, 5, 1))
    assert first
    cached = redis_cache.get(f"search:{s[0].code}:{s[3].code}:2026-05-01")
    assert cached == first
    # Poison the cache; subsequent call must return the poisoned value.
    redis_cache.set(
        f"search:{s[0].code}:{s[3].code}:2026-05-01",
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
        timeout=30,
    )
    second = search_departures(s[0].code, s[3].code, date(2026, 5, 1))
    assert second[0]["uuid"] == "poisoned"


# ---------------------------------------------------------------------------
# bump_departure_generation edge cases
# ---------------------------------------------------------------------------


def test_bump_departure_generation_from_zero() -> None:
    """First bump on a fresh key returns 1."""
    assert get_departure_generation("brand-new-uuid") == 0
    result = bump_departure_generation("brand-new-uuid")
    assert result == 1
    assert get_departure_generation("brand-new-uuid") == 1


def test_bump_departure_generation_increments() -> None:
    """Successive bumps increment the counter."""
    bump_departure_generation("inc-uuid")
    bump_departure_generation("inc-uuid")
    result = bump_departure_generation("inc-uuid")
    assert result == 3
    assert get_departure_generation("inc-uuid") == 3


# ---------------------------------------------------------------------------
# _get_or_set: empty list is cached (not treated as miss)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_empty_result_cached(
    stations: list[Station], departure: Departure
) -> None:
    """An empty departure list is still cached (empty list != None)."""
    s = stations
    # Search for a date with no departures
    result = search_departures(s[0].code, s[3].code, date(2099, 1, 1))
    assert result == []
    # The empty list should be in the cache
    cached = redis_cache.get(f"search:{s[0].code}:{s[3].code}:2099-01-01")
    assert cached == []
