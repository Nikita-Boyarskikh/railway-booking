"""Performance regression tests: exact/bounded query counts on hot paths.

These tests pin the SHAPE of query counts on the request-processing hot
paths (``search_departures``, ``list_seats``, ``create_order``, the
stations endpoint) so that a regression to N+1 queries — from breaking a
``prefetch_related``, dropping a cache decorator, or re-introducing a
per-row lookup — fails loudly instead of silently eating CPU in prod.
"""

from datetime import date, time

import pytest
from django.conf import settings
from django.core.cache import caches
from pytest_django import DjangoAssertNumQueries
from rest_framework.test import APIClient

from apps.bookings.models import Booking, Order, Passenger
from apps.bookings.services import create_order
from apps.core.availability import free_seat_ids, make_segment_range
from apps.core.timetable import compute_timetable
from apps.routes.services import resolve_station_range
from apps.stations.models import Station
from apps.trains.models import Car, Departure, Seat, Train
from apps.trains.services import list_seats, search_departures
from tests.conftest import make_order_item


def _clear_all_caches() -> None:
    """Clear every configured cache backend (used between cold/warm assertions)."""
    for backend in caches.all():
        backend.clear()


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_query_count_constant_in_bookings(
    station_a: Station,
    station_b: Station,
    station_c: Station,
    station_d: Station,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
    django_assert_max_num_queries: DjangoAssertNumQueries,
) -> None:
    """Query count for ``search_departures`` must not grow with booking count."""
    # Baseline: with zero bookings, call once to warm any lazy imports.
    # stations by code + route + (route_segments, connections, cars, seats) prefetch
    # + free_seat_ids overlap probe + constance = 8 queries total.
    with django_assert_max_num_queries(8):
        results_empty = search_departures(station_a.code, station_d.code, departure.date)
    assert results_empty
    assert results_empty[0]["free_seat_count"] == 2

    # Create N bookings on various (seat, segment) combinations. We only have
    # two seats in the fixture, so alternate seats and segments to spread the
    # load while keeping every pair non-overlapping enough to succeed.
    order = Order.objects.create()
    seats = [seat, seat2]
    ranges = [(station_a, station_b), (station_b, station_c), (station_c, station_d)]

    route = departure.train.route
    created = 0
    for i in range(10):
        s_obj = seats[i % 2]
        station_from, station_to = ranges[i % 3]
        # Skip duplicates (same seat+range combo) to avoid unique conflicts.
        if Booking.objects.filter(
            departure=departure,
            seat=s_obj,
            station_from=station_from,
            station_to=station_to,
        ).exists():
            continue
        from_order, to_order = resolve_station_range(route, station_from.pk, station_to.pk)
        route_segment_exists = from_order is not None and to_order is not None
        assert route_segment_exists, "test fixture requested an impossible route segment"
        passenger = Passenger.objects.create(
            name=f"P{i}",
            passport_number=f"P{i:05d}",
            gender="male",
            birth_date=date.fromisoformat("1990-01-01"),
        )
        Booking.objects.create(
            order=order,
            departure=departure,
            seat=s_obj,
            station_from=station_from,
            station_to=station_to,
            passenger=passenger,
            segment_range=make_segment_range(from_order, to_order),
        )
        created += 1

    assert created > 0

    # With many bookings, the query count must stay under the same ceiling.
    with django_assert_max_num_queries(8):
        results_full = search_departures(station_a.code, station_d.code, departure.date)
    assert results_full


# ---------------------------------------------------------------------------
# search_departures — cold vs warm, scaling in departures
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_warm_cache_zero_queries(
    station_a: Station,
    station_d: Station,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
    django_assert_num_queries: DjangoAssertNumQueries,
    django_assert_max_num_queries: DjangoAssertNumQueries,
) -> None:
    """Cache hit on the search endpoint must not hit the DB at all."""
    # Cold path — bounded.
    # stations by code + route + (route_segments, connections, cars, seats) prefetch
    # + free_seat_ids overlap probe + constance = 8 queries total.
    with django_assert_max_num_queries(8):
        first = search_departures(station_a.code, station_d.code, departure.date)
    assert first

    # Warm path — served from SearchCache, zero queries.
    with django_assert_num_queries(0):
        second = search_departures(station_a.code, station_d.code, departure.date)
    assert second == first


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_query_count_constant_in_departures(
    station_a: Station,
    station_d: Station,
    train: Train,
    car: Car,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
    django_assert_max_num_queries: DjangoAssertNumQueries,
) -> None:
    """Adding more departures on the same route must not add per-departure
    query overhead (prefetch_related must cover route_segments, cars, seats,
    and compute_timetable must use the prefetched chain).

    A small constant slack is allowed for the per-departure
    ``free_seat_ids`` overlap query — that one scales linearly today and is
    flagged as a batching opportunity in the perf plan.
    """
    # Baseline: one departure.
    # stations by code + route + (route_segments, connections, cars, seats) prefetch
    # + free_seat_ids overlap probe + constance = 8 queries total.
    _clear_all_caches()
    with django_assert_max_num_queries(8) as ctx_baseline:
        baseline_results = search_departures(station_a.code, station_d.code, departure.date)
    assert len(baseline_results) == 1
    baseline = len(ctx_baseline.captured_queries)

    # Add four more departures sharing the same train, same date.
    hours = (12, 14, 16, 18)
    for hour in hours:
        Departure.objects.create(
            train=train,
            date=departure.date,
            departure_time=time(hour, 0),
        )

    _clear_all_caches()
    with django_assert_max_num_queries(baseline + len(hours)):
        scaled_results = search_departures(station_a.code, station_d.code, departure.date)
    assert len(scaled_results) == 5


# ---------------------------------------------------------------------------
# list_seats — cold vs warm, single departure
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_list_seats_warm_cache_zero_queries(
    station_a: Station,
    station_d: Station,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
    django_assert_num_queries: DjangoAssertNumQueries,
    django_assert_max_num_queries: DjangoAssertNumQueries,
) -> None:
    """``list_seats`` hits the DB only on cold calls; subsequent calls with
    the same generation counter serve from SeatsCache with zero queries."""
    _clear_all_caches()
    with django_assert_max_num_queries(8):
        list_seats(departure.uuid, station_a.code, station_d.code)

    with django_assert_num_queries(0):
        list_seats(departure.uuid, station_a.code, station_d.code)


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_list_seats_query_count_constant_in_bookings(
    station_a: Station,
    station_b: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
    passenger: Passenger,
    django_assert_max_num_queries: DjangoAssertNumQueries,
) -> None:
    """``list_seats`` query count is independent of booking density on the
    departure — overlap check is a single indexed GiST probe, not a
    per-booking Python loop."""
    _clear_all_caches()
    # departure + from/to stations + (route_segments, connections, cars, seats) prefetch
    # + free_seat_ids overlap probe + constance = 8 queries total
    with django_assert_max_num_queries(8) as ctx_empty:
        list_seats(departure.uuid, station_a.code, station_d.code)
    empty = len(ctx_empty.captured_queries)

    # Fill one seat on the non-conflicting A->B segment.
    create_order(
        departure.uuid,
        station_a.code,
        station_b.code,
        [make_order_item(car.number, seat.number, passenger)],
    )

    _clear_all_caches()
    with django_assert_max_num_queries(8) as ctx_with_booking:
        list_seats(departure.uuid, station_a.code, station_d.code)
    with_booking = len(ctx_with_booking.captured_queries)

    assert with_booking <= empty, (
        f"list_seats got slower with one booking: {empty} → {with_booking}"
    )


# ---------------------------------------------------------------------------
# free_seat_ids — prefetch awareness
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_free_seat_ids_uses_prefetched_cars_and_seats(
    departure: Departure,
    seat: Seat,
    seat2: Seat,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    """When the caller has prefetched ``train__cars__seats``, the overlap
    probe is the ONLY query ``free_seat_ids`` must issue.

    The fixture ``departure`` is re-fetched here so we control the prefetch
    state explicitly and don't rely on test-scope caching.
    """
    dep = (
        Departure.objects.select_related("train")
        .prefetch_related("train__cars__seats")
        .get(pk=departure.pk)
    )
    with django_assert_num_queries(1):
        free_seat_ids(dep, 0, 3)


@pytest.mark.django_db
def test_free_seat_ids_without_prefetch_two_queries(
    departure: Departure,
    seat: Seat,
    seat2: Seat,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    """Without a prefetch chain, ``free_seat_ids`` issues exactly two queries:
    one for the train's seats, one for the booking overlap."""
    dep = Departure.objects.select_related("train").get(pk=departure.pk)
    with django_assert_num_queries(2):
        free_seat_ids(dep, 0, 3)


# ---------------------------------------------------------------------------
# compute_timetable — prefetch awareness
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_compute_timetable_uses_prefetched_route_segments(
    departure: Departure,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    """When route_segments are prefetched, compute_timetable issues zero queries."""
    dep = (
        Departure.objects.select_related("train__route")
        .prefetch_related("train__route__route_segments__connection")
        .get(pk=departure.pk)
    )
    with django_assert_num_queries(0):
        compute_timetable(dep)


@pytest.mark.django_db
def test_compute_timetable_without_prefetch_one_query(
    departure: Departure,
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    """Without prefetch, compute_timetable issues exactly one query for the
    route_segments chain (select_related pulls segment + stations in-query)."""
    dep = Departure.objects.select_related("train__route").get(pk=departure.pk)
    with django_assert_num_queries(1):
        compute_timetable(dep)


# ---------------------------------------------------------------------------
# create_order — query count bounded by item count
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_create_order_query_count_bounded(
    station_a: Station,
    station_b: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    seat2: Seat,
    departure: Departure,
    passenger: Passenger,
    django_assert_max_num_queries: DjangoAssertNumQueries,
) -> None:
    """``create_order`` issues a bounded number of queries that grows
    linearly with the number of items (one seat lookup + one passenger
    insert + one booking insert per item), plus a small constant for the
    departure/stations/order lookups."""
    # Single-item order — establish a baseline.
    # savepoint start/end + departure + from/to stations + (route_segments, connections) prefetch
    # + constance + seat lookup + (order, booking, passenger) insert = 11 queries total.
    _clear_all_caches()
    with django_assert_max_num_queries(11) as ctx_single:
        create_order(
            departure.uuid,
            station_a.code,
            station_b.code,
            [make_order_item(car.number, seat.number, passenger)],
        )
    single_item = len(ctx_single.captured_queries)

    # Two-item order on the remaining free seats (B->D avoids the overlap
    # since the first call already took seat A->B).
    _clear_all_caches()
    with django_assert_max_num_queries(single_item + 3):
        create_order(
            departure.uuid,
            station_b.code,
            station_d.code,
            [
                make_order_item(car.number, seat.number, passenger),
                make_order_item(car.number, seat2.number, passenger),
            ],
        )


# ---------------------------------------------------------------------------
# GET /api/v1/stations/ — hot endpoint, should serve from cache
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_stations_endpoint_warm_cache_zero_queries(
    station_a: Station,
    station_b: Station,
    station_c: Station,
    station_d: Station,
    django_assert_num_queries: DjangoAssertNumQueries,
    django_assert_max_num_queries: DjangoAssertNumQueries,
) -> None:
    """``GET /api/v1/stations/`` serves from StationsCache after the first hit.

    Cold path issues at most one query (the ordered Station list). Every
    subsequent call must return zero queries until a Station mutation fires
    the invalidation signal.
    """
    api_client = APIClient()

    _clear_all_caches()
    with django_assert_max_num_queries(3):
        r1 = api_client.get(f"/api/v{settings.API_VERSION}/stations/")
    assert r1.status_code == 200, r1.json()

    with django_assert_num_queries(0):
        r2 = api_client.get(f"/api/v{settings.API_VERSION}/stations/")
    assert r2.status_code == 200, r2.json()
    assert r2.json() == r1.json()
