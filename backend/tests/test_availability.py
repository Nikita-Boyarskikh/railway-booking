"""Tests for seat availability: resolve_station_range, free_seat_ids, and create_order integration."""

import pytest

from apps.bookings.exceptions import SeatUnavailableError
from apps.bookings.models import Passenger
from apps.bookings.services import create_order
from apps.core.availability import free_seat_ids
from apps.routes.exceptions import InvalidStationRangeError
from apps.routes.models import Route
from apps.routes.services import resolve_station_range
from apps.stations.models import Station
from apps.trains.models import Car, Departure, Seat
from tests.conftest import create_booking, make_order_item

# ---------------------------------------------------------------------------
# resolve_station_range — unit tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_resolve_station_range_valid(
    route: Route,
    station_a: Station,
    station_d: Station,
) -> None:
    """A->D on the full route returns (0, 3)."""
    result = resolve_station_range(route, station_a.pk, station_d.pk)
    assert result == (0, 3)


@pytest.mark.django_db
def test_resolve_station_range_partial(
    route: Route,
    station_b: Station,
    station_d: Station,
) -> None:
    """B->D returns (1, 3) — partial route."""
    result = resolve_station_range(route, station_b.pk, station_d.pk)
    assert result == (1, 3)


@pytest.mark.django_db
def test_resolve_station_range_reversed(
    route: Route,
    station_a: Station,
    station_d: Station,
) -> None:
    """D->A (reverse direction) raises InvalidStationRangeError"""
    with pytest.raises(InvalidStationRangeError):
        resolve_station_range(route, station_d.pk, station_a.pk)


@pytest.mark.django_db
def test_resolve_station_range_same_station(
    route: Route,
    station_a: Station,
) -> None:
    """A->A raises InvalidStationRangeError"""
    with pytest.raises(InvalidStationRangeError):
        resolve_station_range(route, station_a.pk, station_a.pk)


@pytest.mark.django_db
def test_resolve_station_range_not_on_route(route: Route, db: None) -> None:
    """Station not on the route raises InvalidStationRangeError"""
    orphan = Station.objects.create(name="Orphan", code="ORP")
    with pytest.raises(InvalidStationRangeError):
        resolve_station_range(route, orphan.pk, orphan.pk)


# ---------------------------------------------------------------------------
# free_seat_ids — unit tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_free_seat_ids_all_free(
    departure: Departure,
    seat: Seat,
    seat2: Seat,
) -> None:
    """No bookings — all seats are free."""
    free = free_seat_ids(departure, 0, 3)
    assert free == {seat.pk, seat2.pk}


@pytest.mark.django_db
def test_free_seat_ids_adjacent_non_overlapping(
    station_a: Station,
    station_b: Station,
    departure: Departure,
    seat: Seat,
    seat2: Seat,
    passenger: Passenger,
) -> None:
    """Seat booked A->B is free for B->C (adjacent, non-overlapping)."""
    create_booking(departure, seat, station_a, station_b, passenger)
    # Query for B->C (orders 1..2)
    free = free_seat_ids(departure, 1, 2)
    assert seat.pk in free
    assert seat2.pk in free


@pytest.mark.django_db
def test_free_seat_ids_exact_overlap(
    station_a: Station,
    station_c: Station,
    departure: Departure,
    seat: Seat,
    seat2: Seat,
    passenger: Passenger,
) -> None:
    """Seat booked A->C is occupied for A->C (exact overlap)."""
    create_booking(departure, seat, station_a, station_c, passenger)
    free = free_seat_ids(departure, 0, 2)
    assert seat.pk not in free
    assert seat2.pk in free


@pytest.mark.django_db
def test_free_seat_ids_partial_overlap(
    station_a: Station,
    station_c: Station,
    departure: Departure,
    seat: Seat,
    seat2: Seat,
    passenger: Passenger,
) -> None:
    """Seat booked A->C is occupied for B->D (partial overlap at B->C)."""
    create_booking(departure, seat, station_a, station_c, passenger)
    free = free_seat_ids(departure, 1, 3)
    assert seat.pk not in free
    assert seat2.pk in free


@pytest.mark.django_db
def test_free_seat_ids_multiple_bookings_different_seats(
    station_a: Station,
    station_d: Station,
    departure: Departure,
    seat: Seat,
    seat2: Seat,
    passenger: Passenger,
) -> None:
    """Both seats booked on overlapping segments — none free."""
    create_booking(departure, seat, station_a, station_d, passenger)
    create_booking(departure, seat2, station_a, station_d, passenger)
    free = free_seat_ids(departure, 0, 3)
    assert free == set()


# ---------------------------------------------------------------------------
# Integration tests (via create_order)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_non_overlapping_segments_share_seat(
    station_a: Station,
    station_b: Station,
    station_c: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    item = make_order_item(car.number, seat.number, passenger)
    create_order(departure.uuid, station_a.code, station_b.code, [item])
    create_order(departure.uuid, station_c.code, station_d.code, [item])


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
def test_overlapping_segments_conflict(
    station_a: Station,
    station_b: Station,
    station_c: Station,
    station_d: Station,
    car: Car,
    seat: Seat,
    departure: Departure,
    passenger: Passenger,
) -> None:
    item = make_order_item(car.number, seat.number, passenger)
    create_order(departure.uuid, station_a.code, station_c.code, [item])
    with pytest.raises(SeatUnavailableError):
        create_order(departure.uuid, station_b.code, station_d.code, [item])
