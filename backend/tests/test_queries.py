"""Regression tests guarding against N+1 growth in pricing/availability."""

from datetime import date

import pytest
from psycopg.types.range import Range
from pytest_django import DjangoAssertNumQueries

from apps.bookings.models import Booking, Order, Passenger
from apps.core.availability import resolve_station_range
from apps.stations.models import Station
from apps.trains.models import Departure, Seat
from apps.trains.services import search_departures


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_search_departures_query_count_constant_in_bookings(
    stations: list[Station],
    seat: Seat,
    seat2: Seat,
    departure: Departure,
    django_assert_max_num_queries: DjangoAssertNumQueries,
) -> None:
    """Query count for ``search_departures`` must not grow with booking count."""
    s = stations

    # Baseline: with zero bookings, call once to warm any lazy imports.
    with django_assert_max_num_queries(20):
        results_empty = search_departures(s[0].code, s[3].code, date(2026, 5, 1))
    assert results_empty
    assert results_empty[0]["free_seat_count"] == 2

    # Create N bookings on various (seat, segment) combinations. We only have
    # two seats in the fixture, so alternate seats and segments to spread the
    # load while keeping every pair non-overlapping enough to succeed.
    order = Order.objects.create()
    seats = [seat, seat2]
    ranges = [(s[0], s[1]), (s[1], s[2]), (s[2], s[3])]

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
        rng = resolve_station_range(route, station_from.id, station_to.id)
        assert rng is not None
        from_order, to_order = rng
        passenger = Passenger.objects.create(
            name=f"P{i}",
            passport_number=f"P{i:05d}",
            gender="male",
            birth_date=date(1990, 1, 1),
        )
        Booking.objects.create(
            order=order,
            departure=departure,
            seat=s_obj,
            station_from=station_from,
            station_to=station_to,
            passenger=passenger,
            segment_range=Range(from_order, to_order, bounds="[)"),
        )
        created += 1

    assert created > 0

    # With many bookings, the query count must stay under the same ceiling.
    with django_assert_max_num_queries(20):
        results_full = search_departures(s[0].code, s[3].code, date(2026, 5, 1))
    assert results_full
