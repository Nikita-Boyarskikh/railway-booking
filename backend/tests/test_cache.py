"""Tests for the Redis-backed cache layer (locmem in the test settings)."""

from datetime import date

import pytest
from django.core.cache import cache

from apps.bookings.services import create_order
from apps.core.cache import STATIONS_KEY, get_departure_generation
from apps.stations.models import Station
from apps.trains.services import list_seats, search_departures


@pytest.fixture(autouse=True)
def _clear_cache():
    """Wipe the process-local cache between tests so they don't bleed state."""
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
def test_stations_cache_invalidated_on_station_change(demo_data):
    """Creating or deleting a Station drops the cached stations:all entry."""
    cache.set(STATIONS_KEY, [{"name": "stale", "code": "STL"}], timeout=300)
    Station.objects.create(name="New", code="NEW")
    assert cache.get(STATIONS_KEY) is None

    cache.set(STATIONS_KEY, [{"name": "stale2", "code": "STL2"}], timeout=300)
    Station.objects.filter(code="NEW").delete()
    assert cache.get(STATIONS_KEY) is None


@pytest.mark.django_db(transaction=True)
def test_list_seats_cached_and_invalidated_on_booking(demo_data):
    """``list_seats`` hits the cache on repeat calls; a booking bumps the generation."""
    d = demo_data
    s = d["stations"]

    first = list_seats(d["departure"], s[0].code, s[3].code)
    # Mutate the in-cache entry to prove the next call returns *this* value.
    cache_hit_marker = {"cars": [{"marker": "cached"}]}
    # Find the key the service stored under and overwrite it.
    gen = get_departure_generation(str(d["departure"].uuid))
    key = f"seats:{d['departure'].uuid}:{s[0].code}:{s[3].code}:g{gen}"
    cache.set(key, cache_hit_marker, timeout=60)

    second = list_seats(d["departure"], s[0].code, s[3].code)
    assert second == cache_hit_marker, "expected cache hit on second call"
    assert second != first

    # Booking bumps the generation; the old key orphans and a fresh load runs.
    create_order(
        d["departure"].uuid,
        s[0].code,
        s[1].code,
        [
            {
                "car_number": d["car"].number,
                "seat_number": d["seat"].number,
                "passenger_name": "C",
                "passenger_passport": "Z",
                "passenger_gender": "male",
                "passenger_birth_date": "1990-01-01",
            }
        ],
    )
    assert get_departure_generation(str(d["departure"].uuid)) > gen
    third = list_seats(d["departure"], s[0].code, s[3].code)
    assert third != cache_hit_marker, "expected fresh data after generation bump"
    assert "cars" in third


@pytest.mark.django_db
def test_search_departures_cached(demo_data):
    """``search_departures`` caches its output under ``search:{from}:{to}:{date}``."""
    d = demo_data
    s = d["stations"]

    first = search_departures(s[0].code, s[3].code, date(2026, 5, 1))
    assert first
    cached = cache.get(f"search:{s[0].code}:{s[3].code}:2026-05-01")
    assert cached == first
    # Poison the cache; subsequent call must return the poisoned value.
    cache.set(
        f"search:{s[0].code}:{s[3].code}:2026-05-01",
        [{"marker": "poisoned", "train_number": "X", "train_name": "X"}],
        timeout=30,
    )
    second = search_departures(s[0].code, s[3].code, date(2026, 5, 1))
    assert second[0]["marker"] == "poisoned"
