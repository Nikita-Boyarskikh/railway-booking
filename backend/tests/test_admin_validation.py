"""Tests for admin-level model validation: RouteSegmentFormSet and Booking.clean()."""

import datetime
from typing import TYPE_CHECKING

import pytest
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.utils import timezone

from apps.bookings.models import Booking, Passenger
from apps.routes.admin import RouteSegmentFormSet, RouteSegmentInline
from apps.routes.models import Route, RouteSegment
from tests.factories import (
    BookingFactory,
    CarFactory,
    ConnectionFactory,
    DepartureFactory,
    OrderFactory,
    RouteFactory,
    RouteSegmentFactory,
    SeatFactory,
    StationFactory,
    TrainFactory,
)

if TYPE_CHECKING:
    from django.forms import BaseInlineFormSet, ModelForm

    from apps.stations.models import Connection, Station
    from apps.trains.models import Car, Departure, Seat


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
    other_route = RouteFactory(name="Other")
    conn = ConnectionFactory(station_from=station_a, station_to=station_d)
    RouteSegmentFactory(route=other_route, connection=conn, order=0)
    other_train = TrainFactory(route=other_route)
    other_car = CarFactory(train=other_train)
    other_seat = SeatFactory(car=other_car)

    booking = Booking(
        order=OrderFactory(),
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
    orphan_x = StationFactory()
    orphan_y = StationFactory()

    booking = Booking(
        order=OrderFactory(),
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
        order=OrderFactory(),
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
        order=OrderFactory(),
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
        order=OrderFactory(),
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
        order=OrderFactory(),
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
    orphan = StationFactory()
    conn = ConnectionFactory(station_from=orphan, station_to=orphan)
    other_route = RouteFactory()
    RouteSegmentFactory(route=other_route, connection=conn, order=0)
    other_train = TrainFactory(route=other_route)
    other_car = CarFactory(train=other_train)
    other_seat = SeatFactory(car=other_car)

    booking = Booking(
        order=OrderFactory(),
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
    train = TrainFactory(route=route)
    car = CarFactory(train=train)
    seat = SeatFactory(car=car)
    departure = DepartureFactory(train=train)

    first_seg = route.route_segments.order_by("order").first()
    last_seg = route.route_segments.order_by("order").last()
    assert first_seg is not None
    assert last_seg is not None

    return BookingFactory(
        departure=departure,
        seat=seat,
        station_from=first_seg.connection.station_from,
        station_to=last_seg.connection.station_to,
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


# ===========================================================================
# Passenger validators — passport_number, birth_date
# ===========================================================================


@pytest.mark.django_db
@pytest.mark.parametrize(
    "bad_passport",
    ["", "abc", "ABC/123", "12@3456"],
    ids=["empty", "too_short", "slash", "at_sign"],
)
def test_passenger_passport_number_invalid(bad_passport: str) -> None:
    """Passport numbers with disallowed characters or below min length are rejected."""
    passenger = Passenger(
        name="John",
        passport_number=bad_passport,
        gender="male",
        birth_date=datetime.date(1990, 1, 1),
    )
    with pytest.raises(ValidationError) as exc_info:
        passenger.full_clean()
    assert "passport_number" in exc_info.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize(
    "ok_passport",
    ["1234", "AB-123456", "ABC 12 34", "PP1234567890"],
    ids=["digits_only", "dash", "spaces", "mixed"],
)
def test_passenger_passport_number_valid(ok_passport: str) -> None:
    """Well-formed passport numbers pass validation."""
    Passenger(
        name="John",
        passport_number=ok_passport,
        gender="male",
        birth_date=datetime.date(1990, 1, 1),
    ).full_clean()


@pytest.mark.django_db
def test_passenger_birth_date_today_rejected() -> None:
    """Birth date equal to today is rejected — must be strictly in the past."""
    passenger = Passenger(
        name="John",
        passport_number="1234567890",
        gender="male",
        birth_date=timezone.localdate(),
    )
    with pytest.raises(ValidationError) as exc_info:
        passenger.full_clean()
    assert "birth_date" in exc_info.value.message_dict


@pytest.mark.django_db
def test_passenger_birth_date_future_rejected() -> None:
    """Birth date in the future is rejected."""
    passenger = Passenger(
        name="John",
        passport_number="1234567890",
        gender="male",
        birth_date=timezone.localdate() + datetime.timedelta(days=1),
    )
    with pytest.raises(ValidationError) as exc_info:
        passenger.full_clean()
    assert "birth_date" in exc_info.value.message_dict


@pytest.mark.django_db
def test_passenger_birth_date_past_accepted() -> None:
    """A birth date strictly in the past passes validation."""
    Passenger(
        name="John",
        passport_number="1234567890",
        gender="male",
        birth_date=timezone.localdate() - datetime.timedelta(days=1),
    ).full_clean()
