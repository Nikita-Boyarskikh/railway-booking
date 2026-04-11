"""Tests for seat availability: resolve_station_range, free_seat_ids, and create_order integration."""

from datetime import date

import pytest
from psycopg.types.range import Range

from apps.bookings.models import Booking, Order, Passenger
from apps.bookings.services import SeatUnavailableError, create_order
from apps.core.availability import free_seat_ids, resolve_station_range
from apps.routes.models import Route
from apps.stations.models import Station
from apps.trains.models import Car, Departure, Seat
from tests.conftest import make_order_item

# ---------------------------------------------------------------------------
# resolve_station_range — unit tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resolve_station_range_valid(
    route: Route,
    stations: list[Station],
) -> None:
    """A->D on the full route returns (0, 3)."""
    result = resolve_station_range(route, stations[0].id, stations[3].id)
    assert result == (0, 3)


@pytest.mark.django_db
def test_resolve_station_range_partial(
    route: Route,
    stations: list[Station],
) -> None:
    """B->D returns (1, 3) — partial route."""
    result = resolve_station_range(route, stations[1].id, stations[3].id)
    assert result == (1, 3)


@pytest.mark.django_db
def test_resolve_station_range_reversed(
    route: Route,
    stations: list[Station],
) -> None:
    """D->A (reverse direction) returns None."""
    result = resolve_station_range(route, stations[3].id, stations[0].id)
    assert result is None


@pytest.mark.django_db
def test_resolve_station_range_same_station(
    route: Route,
    stations: list[Station],
) -> None:
    """A->A returns None."""
    result = resolve_station_range(route, stations[0].id, stations[0].id)
    assert result is None


@pytest.mark.django_db
def test_resolve_station_range_not_on_route(route: Route, db: None) -> None:
    """Station not on the route returns None."""
    orphan = Station.objects.create(name="Orphan", code="ORP")
    result = resolve_station_range(route, orphan.id, orphan.id)
    assert result is None


# ---------------------------------------------------------------------------
# free_seat_ids — unit tests
# ---------------------------------------------------------------------------


def _book(
    departure: Departure,
    seat: Seat,
    station_from: Station,
    station_to: Station,
) -> None:
    """Create a minimal Booking for testing (bypasses service layer)."""
    order = Order.objects.create()
    passenger = Passenger.objects.create(
        name="Test",
        passport_number="T",
        gender="male",
        birth_date=date(1990, 1, 1),
    )
    rng = resolve_station_range(departure.train.route, station_from.id, station_to.id)
    assert rng is not None, "test fixture requested an impossible route segment"
    from_order, to_order = rng
    Booking.objects.create(
        order=order,
        departure=departure,
        seat=seat,
        station_from=station_from,
        station_to=station_to,
        passenger=passenger,
        segment_range=Range(from_order, to_order, bounds="[)"),
    )


@pytest.mark.django_db
def test_free_seat_ids_all_free(
    departure: Departure,
    seat: Seat,
    seat2: Seat,
) -> None:
    """No bookings — all seats are free."""
    free = free_seat_ids(departure, 0, 3)
    assert free == {seat.id, seat2.id}


@pytest.mark.django_db
def test_free_seat_ids_adjacent_non_overlapping(
    stations: list[Station],
    departure: Departure,
    seat: Seat,
    seat2: Seat,
) -> None:
    """Seat booked A->B is free for B->C (adjacent, non-overlapping)."""
    _book(departure, seat, stations[0], stations[1])
    # Query for B->C (orders 1..2)
    free = free_seat_ids(departure, 1, 2)
    assert seat.id in free
    assert seat2.id in free


@pytest.mark.django_db
def test_free_seat_ids_exact_overlap(
    stations: list[Station],
    departure: Departure,
    seat: Seat,
    seat2: Seat,
) -> None:
    """Seat booked A->C is occupied for A->C (exact overlap)."""
    _book(departure, seat, stations[0], stations[2])
    free = free_seat_ids(departure, 0, 2)
    assert seat.id not in free
    assert seat2.id in free


@pytest.mark.django_db
def test_free_seat_ids_partial_overlap(
    stations: list[Station],
    departure: Departure,
    seat: Seat,
    seat2: Seat,
) -> None:
    """Seat booked A->C is occupied for B->D (partial overlap at B->C)."""
    _book(departure, seat, stations[0], stations[2])
    free = free_seat_ids(departure, 1, 3)
    assert seat.id not in free
    assert seat2.id in free


@pytest.mark.django_db
def test_free_seat_ids_multiple_bookings_different_seats(
    stations: list[Station],
    departure: Departure,
    seat: Seat,
    seat2: Seat,
) -> None:
    """Both seats booked on overlapping segments — none free."""
    _book(departure, seat, stations[0], stations[3])
    _book(departure, seat2, stations[0], stations[3])
    free = free_seat_ids(departure, 0, 3)
    assert free == set()


# ---------------------------------------------------------------------------
# Integration tests (via create_order)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_non_overlapping_segments_share_seat(
    stations: list[Station],
    car: Car,
    seat: Seat,
    departure: Departure,
) -> None:
    item = make_order_item(car.number, seat.number)
    create_order(departure.uuid, stations[0].code, stations[1].code, [item])
    order2 = create_order(departure.uuid, stations[2].code, stations[3].code, [item])
    assert order2.bookings.count() == 1


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_overlapping_segments_conflict(
    stations: list[Station],
    car: Car,
    seat: Seat,
    departure: Departure,
) -> None:
    item = make_order_item(car.number, seat.number)
    create_order(departure.uuid, stations[0].code, stations[2].code, [item])
    with pytest.raises(SeatUnavailableError):
        create_order(departure.uuid, stations[1].code, stations[3].code, [item])
