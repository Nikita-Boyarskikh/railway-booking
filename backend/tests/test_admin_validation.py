"""Tests for admin-level model validation: RouteSegmentFormSet and Booking.clean()."""

from typing import TYPE_CHECKING

import pytest
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from djmoney.money import Money

from apps.bookings.models import Booking, Order, Passenger
from apps.core.availability import make_segment_range
from apps.routes.admin import RouteSegmentFormSet, RouteSegmentInline
from apps.routes.models import Route, RouteSegment
from apps.stations.models import Connection, Station
from apps.trains.models import Car, Departure, Seat, Train

if TYPE_CHECKING:
    from django.forms import BaseInlineFormSet, ModelForm


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def admin_user(db: None) -> User:
    return User.objects.create_superuser("admin", "admin@test.com", "password")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_formset_data(
    segments: list[tuple[int, Connection]],
    *,
    total_forms: int | None = None,
    initial_forms: int = 0,
    deletions: set[int] | None = None,
    ids: list[int] | None = None,
) -> dict[str, str]:
    """Build the management + per-form POST data for a RouteSegmentFormSet.

    ``segments`` is a list of ``(order, connection)`` tuples.
    ``deletions`` is a set of form indices to mark as DELETE.
    ``ids`` — PK of existing RouteSegment for each form index (for initial forms).
    """
    count = total_forms if total_forms is not None else len(segments)
    data: dict[str, str] = {
        "route_segments-TOTAL_FORMS": str(count),
        "route_segments-INITIAL_FORMS": str(initial_forms),
        "route_segments-MIN_NUM_FORMS": "0",
        "route_segments-MAX_NUM_FORMS": "1000",
    }
    for i, (order, conn) in enumerate(segments):
        prefix = f"route_segments-{i}"
        data[f"{prefix}-order"] = str(order)
        data[f"{prefix}-connection"] = str(conn.pk)
        data[f"{prefix}-stop_duration"] = "00:00:00"
        if ids and i < len(ids):
            data[f"{prefix}-id"] = str(ids[i])
        if deletions and i in deletions:
            data[f"{prefix}-DELETE"] = "on"
    return data


def _validate_formset(route: Route, data: dict[str, str]) -> list[str]:
    """Run RouteSegmentFormSet validation and return non-form errors as strings."""
    from django.forms import inlineformset_factory

    FormSet: type[BaseInlineFormSet[RouteSegment, Route, ModelForm[RouteSegment]]] = (  # noqa: N806
        inlineformset_factory(
            Route,
            RouteSegment,
            formset=RouteSegmentFormSet,
            fields=("connection", "order", "stop_duration"),
            extra=0,
        )
    )
    formset = FormSet(data, instance=route, prefix="route_segments")
    formset.full_clean()
    if formset.is_valid():
        return []
    return [str(e) for e in formset.non_form_errors()]


# ===========================================================================
# RouteSegmentFormSet — valid cases
# ===========================================================================


@pytest.mark.django_db
def test_formset_valid_chain(
    route: Route,
    connection_ab: Connection,
    connection_bc: Connection,
    connection_cd: Connection,
) -> None:
    """A→B (0), B→C (1), C→D (2) — valid continuous chain."""
    data = _make_formset_data(
        [
            (0, connection_ab),
            (1, connection_bc),
            (2, connection_cd),
        ]
    )
    errors = _validate_formset(route, data)
    assert errors == []


@pytest.mark.django_db
def test_formset_single_segment(
    route: Route,
    connection_ab: Connection,
) -> None:
    """A single segment is always a valid chain."""
    data = _make_formset_data([(0, connection_ab)])
    errors = _validate_formset(route, data)
    assert errors == []


# ===========================================================================
# RouteSegmentFormSet — order errors
# ===========================================================================


@pytest.mark.django_db
def test_formset_gap_in_order(
    route: Route,
    connection_ab: Connection,
    connection_bc: Connection,
) -> None:
    """Orders 0, 2 (gap at 1) — rejected."""
    data = _make_formset_data(
        [
            (0, connection_ab),
            (2, connection_bc),
        ]
    )
    errors = _validate_formset(route, data)
    assert any("sequential" in e for e in errors)


@pytest.mark.django_db
def test_formset_duplicate_order(
    route: Route,
    connection_ab: Connection,
    connection_bc: Connection,
) -> None:
    """Both segments with order=0 — rejected."""
    data = _make_formset_data(
        [
            (0, connection_ab),
            (0, connection_bc),
        ]
    )
    errors = _validate_formset(route, data)
    assert any("sequential" in e for e in errors)


@pytest.mark.django_db
def test_formset_not_starting_from_zero(
    route: Route,
    connection_ab: Connection,
    connection_bc: Connection,
) -> None:
    """Orders starting from 1 instead of 0 — rejected."""
    data = _make_formset_data(
        [
            (1, connection_ab),
            (2, connection_bc),
        ]
    )
    errors = _validate_formset(route, data)
    assert any("sequential" in e for e in errors)


# ===========================================================================
# RouteSegmentFormSet — chain continuity errors
# ===========================================================================


@pytest.mark.django_db
def test_formset_broken_chain(
    route: Route,
    connection_ab: Connection,
    connection_cd: Connection,
) -> None:
    """A→B (0), C→D (1) — B≠C break in chain."""
    data = _make_formset_data(
        [
            (0, connection_ab),
            (1, connection_cd),
        ]
    )
    errors = _validate_formset(route, data)
    assert any("not continuous" in e for e in errors)


@pytest.mark.django_db
def test_formset_reversed_segment(
    route: Route,
    connection_ab: Connection,
    connection_bc: Connection,
) -> None:
    """B→C (0), A→B (1) — chain broken (C≠A)."""
    data = _make_formset_data(
        [
            (0, connection_bc),
            (1, connection_ab),
        ]
    )
    errors = _validate_formset(route, data)
    assert any("not continuous" in e for e in errors)


# ===========================================================================
# RouteSegmentFormSet — empty route
# ===========================================================================


@pytest.mark.django_db
def test_formset_empty_route(route: Route) -> None:
    """No segments at all — rejected."""
    data = _make_formset_data([])
    errors = _validate_formset(route, data)
    assert any("empty" in e.lower() for e in errors)


# ===========================================================================
# RouteSegmentFormSet — deletion handling
# ===========================================================================


@pytest.mark.django_db
def test_formset_deleted_forms_ignored(
    route: Route,
    connection_ab: Connection,
    connection_bc: Connection,
    connection_cd: Connection,
) -> None:
    """Deleted forms should not break validation of the remaining chain."""
    data = _make_formset_data(
        [
            (0, connection_ab),
            (1, connection_cd),  # would break chain, but is deleted
            (1, connection_bc),
        ],
        total_forms=3,
        deletions={1},
    )
    # After ignoring form index 1, remaining is A→B(0), B→C(1) — valid.
    errors = _validate_formset(route, data)
    assert errors == []


# ===========================================================================
# Booking.clean() — seat wrong train
# ===========================================================================


@pytest.mark.django_db
def test_booking_clean_seat_wrong_train(
    departure: Departure,
    station_a: Station,
    station_d: Station,
    passenger: Passenger,
) -> None:
    """Seat from a different train is rejected."""
    other_route = Route.objects.create(name="Other")
    conn = Connection.objects.create(
        station_from=station_a,
        station_to=station_d,
        distance_km=100,
        base_price=Money(100, "USD"),
    )
    RouteSegment.objects.create(route=other_route, connection=conn, order=0)
    other_train = Train.objects.create(
        route=other_route,
        number="OTHER",
        name="Other",
        avg_speed_kmh=100,
    )
    other_car = Car.objects.create(train=other_train, number=1)
    other_seat = Seat.objects.create(car=other_car, number=1)

    booking = Booking(
        order=Order.objects.create(),
        departure=departure,
        seat=other_seat,
        station_from=station_a,
        station_to=station_d,
        passenger=passenger,
    )

    with pytest.raises(ValidationError) as exc_info:
        booking.clean()
    assert "seat" in exc_info.value.message_dict


# ===========================================================================
# Booking.clean() — station not on route
# ===========================================================================


@pytest.mark.django_db
def test_booking_clean_station_not_on_route(
    departure: Departure,
    car: Car,
    seat: Seat,
    passenger: Passenger,
) -> None:
    """Stations not on the departure's route are rejected."""
    orphan_x = Station.objects.create(name="X", code="X")
    orphan_y = Station.objects.create(name="Y", code="Y")

    booking = Booking(
        order=Order.objects.create(),
        departure=departure,
        seat=seat,
        station_from=orphan_x,
        station_to=orphan_y,
        passenger=passenger,
    )

    with pytest.raises(ValidationError) as exc_info:
        booking.clean()
    assert "station_from" in exc_info.value.message_dict


# ===========================================================================
# Booking.clean() — reversed station order
# ===========================================================================


@pytest.mark.django_db
def test_booking_clean_reversed_stations(
    departure: Departure,
    car: Car,
    seat: Seat,
    station_a: Station,
    station_d: Station,
    passenger: Passenger,
) -> None:
    """D→A (wrong direction) is rejected."""
    booking = Booking(
        order=Order.objects.create(),
        departure=departure,
        seat=seat,
        station_from=station_d,
        station_to=station_a,
        passenger=passenger,
    )

    with pytest.raises(ValidationError) as exc_info:
        booking.clean()
    assert "station_from" in exc_info.value.message_dict


# ===========================================================================
# Booking.clean() — same station
# ===========================================================================


@pytest.mark.django_db
def test_booking_clean_same_station(
    departure: Departure,
    car: Car,
    seat: Seat,
    station_a: Station,
    passenger: Passenger,
) -> None:
    """A→A (same station) is rejected."""
    booking = Booking(
        order=Order.objects.create(),
        departure=departure,
        seat=seat,
        station_from=station_a,
        station_to=station_a,
        passenger=passenger,
    )

    with pytest.raises(ValidationError) as exc_info:
        booking.clean()
    assert "station_from" in exc_info.value.message_dict


# ===========================================================================
# Booking.clean() — valid booking auto-fills segment_range
# ===========================================================================


@pytest.mark.django_db
def test_booking_clean_valid_auto_fills_segment_range(
    departure: Departure,
    car: Car,
    seat: Seat,
    station_a: Station,
    station_d: Station,
    passenger: Passenger,
) -> None:
    """Valid booking gets segment_range auto-computed by clean()."""
    booking = Booking(
        order=Order.objects.create(),
        departure=departure,
        seat=seat,
        station_from=station_a,
        station_to=station_d,
        passenger=passenger,
    )

    booking.clean()  # should not raise

    assert booking.segment_range is not None
    assert booking.segment_range.lower == 0
    assert booking.segment_range.upper == 3


@pytest.mark.django_db
def test_booking_clean_partial_route_segment_range(
    departure: Departure,
    car: Car,
    seat: Seat,
    station_b: Station,
    station_d: Station,
    passenger: Passenger,
) -> None:
    """B→D gets segment_range [1, 3)."""
    booking = Booking(
        order=Order.objects.create(),
        departure=departure,
        seat=seat,
        station_from=station_b,
        station_to=station_d,
        passenger=passenger,
    )

    booking.clean()

    assert booking.segment_range.lower == 1
    assert booking.segment_range.upper == 3


# ===========================================================================
# Booking.clean() — multiple errors at once
# ===========================================================================


@pytest.mark.django_db
def test_booking_clean_wrong_train_and_wrong_stations(
    departure: Departure,
    passenger: Passenger,
) -> None:
    """Both seat-wrong-train and invalid-stations are reported together."""
    other_route = Route.objects.create(name="Z")
    orphan = Station.objects.create(name="Z", code="Z")
    conn = Connection.objects.create(
        station_from=orphan,
        station_to=orphan,
        distance_km=1,
        base_price=Money(1, "USD"),
    )
    RouteSegment.objects.create(route=other_route, connection=conn, order=0)
    other_train = Train.objects.create(
        route=other_route,
        number="Z",
        name="Z",
        avg_speed_kmh=100,
    )
    other_car = Car.objects.create(train=other_train, number=1)
    other_seat = Seat.objects.create(car=other_car, number=1)

    booking = Booking(
        order=Order.objects.create(),
        departure=departure,
        seat=other_seat,
        station_from=orphan,
        station_to=orphan,
        passenger=passenger,
    )

    with pytest.raises(ValidationError) as exc_info:
        booking.clean()
    # Both errors present
    assert "seat" in exc_info.value.message_dict
    assert "station_from" in exc_info.value.message_dict


# ===========================================================================
# RouteSegmentInline — permissions locked when bookings exist
# ===========================================================================


def _create_booking_for_route(route: Route) -> Booking:
    """Create a minimal booking chain: Route → Train → Departure → Booking."""
    train = Train.objects.create(route=route, number="LCK", name="Locked", avg_speed_kmh=100)
    car = Car.objects.create(train=train, number=1)
    seat = Seat.objects.create(car=car, number=1)
    departure = Departure.objects.create(
        train=train,
        date="2026-05-01",
        departure_time="10:00",
    )
    passenger = Passenger.objects.create(
        name="Test",
        passport_number="0000",
        gender="male",
        birth_date="1990-01-01",
    )

    first_seg = route.route_segments.order_by("order").first()
    last_seg = route.route_segments.order_by("order").last()
    assert first_seg is not None
    assert last_seg is not None

    return Booking.objects.create(
        order=Order.objects.create(),
        departure=departure,
        seat=seat,
        station_from_id=first_seg.connection.station_from_id,
        station_to_id=last_seg.connection.station_to_id,
        passenger=passenger,
        segment_range=make_segment_range(0, route.route_segments.count()),
    )


@pytest.fixture
def segment_inline() -> RouteSegmentInline:
    return RouteSegmentInline(Route, admin.site)


@pytest.mark.django_db
def test_inline_readonly_when_bookings_exist(
    route: Route,
    segment_inline: RouteSegmentInline,
) -> None:
    """Cannot add/delete/change segments when bookings exist on the route."""
    _create_booking_for_route(route)
    request = RequestFactory().get("/admin/")
    assert segment_inline.has_add_permission(request, route) is False
    assert segment_inline.has_change_permission(request, route) is False
    assert segment_inline.has_delete_permission(request, route) is False


@pytest.mark.django_db
def test_inline_allows_all_without_bookings(
    route: Route,
    segment_inline: RouteSegmentInline,
    admin_user: User,
) -> None:
    """All permissions granted when no bookings on the route."""
    request = RequestFactory().get("/admin/")
    request.user = admin_user
    assert segment_inline.has_add_permission(request, route) is True
    assert segment_inline.has_change_permission(request, route) is True
    assert segment_inline.has_delete_permission(request, route) is True


@pytest.mark.django_db
def test_inline_allows_all_for_new_route(
    segment_inline: RouteSegmentInline,
    admin_user: User,
) -> None:
    """Permissions granted for a new (unsaved) route."""
    request = RequestFactory().get("/admin/")
    request.user = admin_user
    assert segment_inline.has_add_permission(request, None) is True
    assert segment_inline.has_change_permission(request, None) is True
    assert segment_inline.has_delete_permission(request, None) is True
