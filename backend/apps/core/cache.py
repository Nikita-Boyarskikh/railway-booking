"""Cache helpers built on Django's cache framework (Redis in prod, locmem in tests).

* **Stations** — single key ``stations:all``, invalidated by signals.
* **Departure search** — coarse TTL-only cache keyed by ``(from, to, date)``.
  A few seconds of staleness in free-seat counts is acceptable.
* **Seat listing** — keyed by ``(departure_uuid, from, to, generation)``.
  The generation counter is bumped by :func:`DepartureGenerationCache.incr` from
  :mod:`apps.core.cache` inside ``transaction.on_commit``, so a booking
  immediately invalidates all cached seat maps for that departure. Stale
  entries orphan by suffix and expire on TTL.

The full per-seat bitmask design from the plan is deferred — this layer
shares its invalidation model but caches whole response dicts instead of
individual bit vectors.
"""

import abc
import datetime
from collections.abc import Callable
from typing import Final, cast
from uuid import UUID

from django.core.cache import BaseCache, cache

from apps.core.types import DepartureSummary, SeatsResponse
from apps.routes.models import Route
from apps.stations.models import Station
from config.settings import (
    CACHE_TTL_SEARCH,
    CACHE_TTL_SEATS,
    CACHE_TTL_STATION_ORDER_MAPS,
    CACHE_TTL_STATIONS,
)


class CacheBase[T, **P](abc.ABC):
    """Abstract base for a cache of values of type T, with key-building and invalidation."""

    _MISSING: Final = object()

    cache: BaseCache = cache
    ttl: float | None = None

    @classmethod
    @abc.abstractmethod
    def key(cls, *args: P.args, **kwargs: P.kwargs) -> str:
        """Return the cache key for this call's args."""

    @classmethod
    def invalidate(cls, *args: P.args, **kwargs: P.kwargs) -> None:
        """Invalidate the cache for this call's args."""
        cls.cache.delete(cls.key(*args, **kwargs))

    @classmethod
    def get(cls, *args: P.args, **kwargs: P.kwargs) -> T:
        """Return the cached value for this call's args"""
        return cast(T, cls.cache.get(cls.key(*args, **kwargs)))

    @classmethod
    def set(cls, key: str, value: T) -> None:
        """Set the cached value for this call's args."""
        cls.cache.set(key, value, timeout=cls.ttl)

    @classmethod
    def wrap(cls, func: Callable[P, T]) -> Callable[P, T]:
        """Decorator to cache a function's result under the key for its args, if not already cached."""

        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            key = cls.key(*args, **kwargs)
            hit = cls.cache.get(key, default=cls._MISSING)
            if hit is not cls._MISSING:
                return cast(T, hit)
            value = func(*args, **kwargs)
            cls.set(key, value)
            return value

        return wrapper


class StationsCache(CacheBase[list[Station], []]):
    """Cache for the full station list, invalidated by signals on Station changes."""

    ttl = CACHE_TTL_STATIONS

    @classmethod
    def key(cls) -> str:
        return "stations:all"


class SearchCache(CacheBase[list[DepartureSummary], [str, str, datetime.date]]):
    """Cache for departure search results. A few seconds of staleness is acceptable."""

    ttl = CACHE_TTL_SEARCH

    @classmethod
    def key(cls, from_code: str, to_code: str, date: datetime.date) -> str:
        return f"search:{from_code}:{to_code}:{date.isoformat()}"


class SeatsCache(CacheBase[SeatsResponse, [UUID | str, str, str]]):
    """Cache for departure seat listings, keyed by generation counter and invalidated by bumping it."""

    ttl = CACHE_TTL_SEATS

    @classmethod
    def key(cls, departure_uuid: UUID | str, from_code: str, to_code: str) -> str:
        gen = DepartureGenerationCache.get(departure_uuid)
        return f"seats:{departure_uuid}:{from_code}:{to_code}:{gen}"


type StationOrderMaps = tuple[dict[int, int], dict[int, int]]


class StationOrderMapsCache(CacheBase[StationOrderMaps, [Route]]):
    """Cache for the station-order maps for a route, invalidated by signals on RouteSegment changes."""

    ttl = CACHE_TTL_STATION_ORDER_MAPS

    @classmethod
    def key(cls, route: Route) -> str:
        return f"som:{route.pk}"


class DepartureGenerationCache(CacheBase[int, [str]]):
    """Cache for the generation counter of a departure, incremented on bookings to orphan seat caches."""

    ttl = None  # never expire on its own

    @classmethod
    def key(cls, departure_uuid: str | UUID) -> str:
        return f"dep:gen:{departure_uuid}"

    @classmethod
    def get(cls, departure_uuid: str | UUID) -> int:
        return super().get(str(departure_uuid)) or 0

    @classmethod
    def incr(cls, departure_uuid: str | UUID) -> int:
        """Atomically increment the generation counter for a departure, returning the new value."""
        key = cls.key(departure_uuid)
        try:
            return cls.cache.incr(key)
        except ValueError:
            cls.set(key, 1)
            return 1
