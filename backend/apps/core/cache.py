"""Cache helpers built on Django's cache framework (Redis in prod, locmem in tests).

* **Stations** — single key ``stations:all``, invalidated by signals.
* **Departure search** — coarse TTL-only cache keyed by ``(from, to, date)``.
  A few seconds of staleness in free-seat counts is acceptable.
* **Seat listing** — keyed by ``(departure_uuid, from, to, generation)``.
  The generation counter is bumped by :func:`bump_departure_generation` from
  :mod:`apps.bookings.services` inside ``transaction.on_commit``, so a booking
  immediately invalidates all cached seat maps for that departure. Stale
  entries orphan by suffix and expire on TTL.

The full per-seat bitmask design from the plan is deferred — this layer
shares its invalidation model but caches whole response dicts instead of
individual bit vectors.
"""

from collections.abc import Callable
from typing import Final, cast

from django.core.cache import BaseCache, caches
from django.core.cache.backends.locmem import LocMemCache
from djmoney.money import Money

from apps.routes.models import Route

local_cache = caches["default"]
redis_cache = caches["redis"]

STATIONS_KEY = "stations:all"
STATIONS_TTL = 24 * 60 * 60  # 1 day
SEARCH_TTL = 30  # seconds
SEATS_TTL = 60  # seconds
STATIONS_ORDER_MAPS_TTL = 60  # seconds

_DEP_GEN_TMPL = "dep:gen:{uuid}"
_SEARCH_TMPL = "search:{from_}:{to}:{date}"
_SEATS_TMPL = "seats:{uuid}:{from_}:{to}:g{gen}"
_STATIONS_ORDER_MAPS_TMPL = "som:{route_id}"
_SEGMENT_RANGE_SUBTOTALS_TMPL = "subtotal:{route_id}:{from_order}:{to_order}"

_MISSING: Final = object()


def _get_or_set[T](cache: BaseCache, key: str, loader: Callable[[], T], timeout: int) -> T:
    """Get ``key`` from the cache, populating via ``loader`` on miss.

    Uses an explicit sentinel so legitimately-empty loader results (``[]``,
    ``{}``, ``None``) still cache instead of repopulating on every call.
    """
    hit = cache.get(key, _MISSING)
    if hit is not _MISSING:
        return hit  # type: ignore[no-any-return]
    value = loader()
    cache.set(key, value, timeout=timeout)
    return value


# ---------------------------------------------------------------------------
# Stations
# ---------------------------------------------------------------------------


def cached_stations(loader: Callable[[], list[dict[str, str]]]) -> list[dict[str, str]]:
    """Return the station list, populating the cache on miss."""
    return _get_or_set(redis_cache, STATIONS_KEY, loader, STATIONS_TTL)


def invalidate_stations() -> None:
    """Drop the cached station list (called from post_save/post_delete signals)."""
    redis_cache.delete(STATIONS_KEY)


# ---------------------------------------------------------------------------
# Departure generation counter (used to invalidate per-departure seat caches)
# ---------------------------------------------------------------------------


def _gen_key(departure_uuid: str) -> str:
    return _DEP_GEN_TMPL.format(uuid=departure_uuid)


def get_departure_generation(departure_uuid: str) -> int:
    """Return the current generation counter for ``departure_uuid`` (0 if unset)."""
    return cast(int, redis_cache.get(_gen_key(departure_uuid), 0))


def bump_departure_generation(departure_uuid: str) -> int:
    """Atomically increment the departure's generation counter.

    Called from ``transaction.on_commit`` in :func:`apps.bookings.services.create_order`
    so that previously cached seat maps for this departure orphan immediately.
    """
    key = _gen_key(departure_uuid)
    try:
        return redis_cache.incr(key)
    except ValueError:
        redis_cache.set(key, 1, timeout=None)
        return 1


# ---------------------------------------------------------------------------
# Departure search (free count + min price per day)
# ---------------------------------------------------------------------------


def cached_search_departures[T](
    from_code: str,
    to_code: str,
    date_iso: str,
    loader: Callable[[], T],
) -> T:
    """Cache the full ``search_departures`` response for ``SEARCH_TTL`` seconds."""
    key = _SEARCH_TMPL.format(from_=from_code, to=to_code, date=date_iso)
    return _get_or_set(redis_cache, key, loader, SEARCH_TTL)


# ---------------------------------------------------------------------------
# Seat listing (per-departure occupancy)
# ---------------------------------------------------------------------------


def cached_list_seats[T](
    departure_uuid: str,
    from_code: str,
    to_code: str,
    loader: Callable[[], T],
) -> T:
    """Cache ``list_seats`` for this ``(departure, from, to)`` at the current generation."""
    gen = get_departure_generation(departure_uuid)
    key = _SEATS_TMPL.format(uuid=departure_uuid, from_=from_code, to=to_code, gen=gen)
    return _get_or_set(redis_cache, key, loader, SEATS_TTL)


# ----------------------------------------------------------------------------
# Cache station order maps for a route, used by :func:`apps.trains.services.resolve_station_range`.
# ----------------------------------------------------------------------------

_StationOrderMaps = tuple[dict[int, int], dict[int, int]]

def cached_station_order_maps(route: Route, loader: Callable[[Route], _StationOrderMaps]) -> _StationOrderMaps:
    """Return the station-order maps for one route, caching the result."""
    key = _STATIONS_ORDER_MAPS_TMPL.format(route_id=route.pk)
    return _get_or_set(local_cache, key, lambda: loader(route), STATIONS_ORDER_MAPS_TTL)

def invalidate_station_order_maps(route_id: int) -> None:
    """Drop the cached station-order maps for one route."""
    local_cache.delete(_STATIONS_ORDER_MAPS_TMPL.format(route_id=route_id))


# ----------------------------------------------------------------------------
# Cache segment range subtotals for a route, used by :func:`apps.trains.services.search_departures`.
# ----------------------------------------------------------------------------

def memoized_segment_range_subtotal(loader: Callable[[int, int, int], Money]) -> Callable[[int, int, int], Money]:
    """Return the cached subtotal for one route and station range."""
    subtotal_cache = LocMemCache('segment_range_subtotals', params={})
    def get_memoized_subtotal(route_id: int, from_order: int, to_order: int) -> Money:
        key = _SEGMENT_RANGE_SUBTOTALS_TMPL.format(route_id=route_id, from_order=from_order, to_order=to_order)
        return _get_or_set(subtotal_cache, key, lambda: loader(route_id, from_order, to_order), STATIONS_ORDER_MAPS_TTL)
    return get_memoized_subtotal
