"""Cache helpers built on Django's cache framework (Redis in prod, locmem in tests).

Implements a pragmatic subset of the design in ``docs/PERF_PLAN.md``:

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

from __future__ import annotations

from collections.abc import Callable

from django.core.cache import cache

STATIONS_KEY = "stations:all"
STATIONS_TTL = 24 * 60 * 60  # 1 day
SEARCH_TTL = 30  # seconds
SEATS_TTL = 60  # seconds

_DEP_GEN_TMPL = "dep:gen:{uuid}"
_SEARCH_TMPL = "search:{from_}:{to}:{date}"
_SEATS_TMPL = "seats:{uuid}:{from_}:{to}:g{gen}"


def _get_or_set[T](key: str, loader: Callable[[], T], timeout: int) -> T:
    """Get ``key`` from the cache, populating via ``loader`` on miss."""
    hit = cache.get(key)
    if hit is not None:
        return hit
    value = loader()
    cache.set(key, value, timeout=timeout)
    return value


# ---------------------------------------------------------------------------
# Stations
# ---------------------------------------------------------------------------


def cached_stations(loader: Callable[[], list[dict]]) -> list[dict]:
    """Return the station list, populating the cache on miss."""
    return _get_or_set(STATIONS_KEY, loader, STATIONS_TTL)


def invalidate_stations() -> None:
    """Drop the cached station list (called from post_save/post_delete signals)."""
    cache.delete(STATIONS_KEY)


# ---------------------------------------------------------------------------
# Departure generation counter (used to invalidate per-departure seat caches)
# ---------------------------------------------------------------------------


def _gen_key(departure_uuid: str) -> str:
    return _DEP_GEN_TMPL.format(uuid=departure_uuid)


def get_departure_generation(departure_uuid: str) -> int:
    """Return the current generation counter for ``departure_uuid`` (0 if unset)."""
    return cache.get(_gen_key(departure_uuid), 0)


def bump_departure_generation(departure_uuid: str) -> int:
    """Atomically increment the departure's generation counter.

    Called from ``transaction.on_commit`` in :func:`apps.bookings.services.create_order`
    so that previously cached seat maps for this departure orphan immediately.
    """
    key = _gen_key(departure_uuid)
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=None)
        return 1


# ---------------------------------------------------------------------------
# Departure search (free count + min price per day)
# ---------------------------------------------------------------------------


def cached_search_departures(
    from_code: str,
    to_code: str,
    date_iso: str,
    loader: Callable[[], list[dict]],
) -> list[dict]:
    """Cache the full ``search_departures`` response for ``SEARCH_TTL`` seconds."""
    key = _SEARCH_TMPL.format(from_=from_code, to=to_code, date=date_iso)
    return _get_or_set(key, loader, SEARCH_TTL)


# ---------------------------------------------------------------------------
# Seat listing (per-departure occupancy)
# ---------------------------------------------------------------------------


def cached_list_seats(
    departure_uuid: str,
    from_code: str,
    to_code: str,
    loader: Callable[[], dict],
) -> dict:
    """Cache ``list_seats`` for this ``(departure, from, to)`` at the current generation."""
    gen = get_departure_generation(departure_uuid)
    key = _SEATS_TMPL.format(uuid=departure_uuid, from_=from_code, to=to_code, gen=gen)
    return _get_or_set(key, loader, SEATS_TTL)
