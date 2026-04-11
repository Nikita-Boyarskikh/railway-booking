"""Tests for the Redis-backed cache layer (locmem in the test settings)."""

from datetime import date

import pytest
from django.core.cache import cache

from apps.bookings.services import create_order
from apps.core.cache import STATIONS_KEY, bump_departure_generation, get_departure_generation
from apps.core.types import CarDict, DepartureSummary, SeatsResponse
from apps.stations.models import Station
from apps.trains.models import Car, Departure, Seat
from apps.trains.services import list_seats, search_departures
from tests.conftest import make_order_item


@pytest.mark.django_db
def test_stations_cache_invalidated_on_station_change(stations: list[Station]) -> None:
    """Creating or deleting a Station drops the cached stations:all entry."""
    cache.set(STATIONS_KEY, [{"name": "stale", "code": "STL"}], timeout=300)
    Station.objects.create(name="New", code="NEW")
    assert cache.get(STATIONS_KEY) is None

    cache.set(STATIONS_KEY, [{"name": "stale2", "code": "STL2"}], timeout=300)
    Station.objects.filter(code="NEW").delete()
    assert cache.get(STATIONS_KEY) is None


@pytest.mark.django_db(transaction=True)
@pytest.mark.usefixtures("base_price")
def test_list_seats_cached_and_invalidated_on_booking(
    stations: list[Station], car: Car, seat: Seat, departure: Departure,
) -> None:
    """``list_seats`` hits the cache on repeat calls; a booking bumps the generation."""
    s = stations

    first = list_seats(departure, s[0].code, s[3].code)
    # Mutate the in-cache entry to prove the next call returns *this* value.
    cache_hit_marker = SeatsResponse(
        cars=[CarDict(number=1, car_type="common", features={"from_cache": 1}, seats=[])]
    )
    # Find the key the service stored under and overwrite it.
    gen = get_departure_generation(str(departure.uuid))
    key = f"seats:{departure.uuid}:{s[0].code}:{s[3].code}:g{gen}"
    cache.set(key, cache_hit_marker, timeout=60)

    second = list_seats(departure, s[0].code, s[3].code)
    assert second == cache_hit_marker, "expected cache hit on second call"
    assert second != first

    # Booking bumps the generation; the old key orphans and a fresh load runs.
    create_order(
        departure.uuid,
        s[0].code,
        s[1].code,
        [make_order_item(car.number, seat.number)],
    )
    assert get_departure_generation(str(departure.uuid)) > gen
    third = list_seats(departure, s[0].code, s[3].code)
    assert third != cache_hit_marker, "expected fresh data after generation bump"
    assert "cars" in third


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_cached(stations: list[Station], departure: Departure) -> None:
    """``search_departures`` caches its output under ``search:{from}:{to}:{date}``."""
    s = stations

    first = search_departures(s[0].code, s[3].code, date(2026, 5, 1))
    assert first
    cached = cache.get(f"search:{s[0].code}:{s[3].code}:2026-05-01")
    assert cached == first
    # Poison the cache; subsequent call must return the poisoned value.
    cache.set(
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
def test_search_departures_empty_result_cached(stations: list[Station], departure: Departure) -> None:
    """An empty departure list is still cached (empty list != None)."""
    s = stations
    # Search for a date with no departures
    result = search_departures(s[0].code, s[3].code, date(2099, 1, 1))
    assert result == []
    # The empty list should be in the cache
    cached = cache.get(f"search:{s[0].code}:{s[3].code}:2099-01-01")
    assert cached == []
