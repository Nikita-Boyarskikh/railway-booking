"""Tests for admin custom logic — ``_bulk_create_seats``."""

import pytest

from apps.trains.admin import _bulk_create_seats
from apps.trains.models import Car, Seat


@pytest.mark.django_db
def test_bulk_create_seats_creates_correct_numbers(car: Car) -> None:
    """Creates seats 1..N on an empty car."""
    _bulk_create_seats(car, 5)
    numbers = sorted(car.seats.values_list("number", flat=True))
    assert numbers == [1, 2, 3, 4, 5]


@pytest.mark.django_db
def test_bulk_create_seats_skips_existing(car: Car) -> None:
    """Pre-existing seat numbers are not duplicated."""
    Seat.objects.create(car=car, number=2)
    Seat.objects.create(car=car, number=4)

    _bulk_create_seats(car, 5)

    numbers = sorted(car.seats.values_list("number", flat=True))
    assert numbers == [1, 2, 3, 4, 5]


@pytest.mark.django_db
def test_bulk_create_seats_idempotent(car: Car) -> None:
    """Calling twice with the same N doesn't duplicate seats."""
    _bulk_create_seats(car, 3)
    _bulk_create_seats(car, 3)
    assert car.seats.count() == 3


@pytest.mark.django_db
def test_bulk_create_seats_zero_does_nothing(car: Car) -> None:
    _bulk_create_seats(car, 0)
    assert car.seats.count() == 0


@pytest.mark.django_db
def test_bulk_create_seats_negative_does_nothing(car: Car) -> None:
    _bulk_create_seats(car, -1)
    assert car.seats.count() == 0


@pytest.mark.django_db
def test_bulk_create_seats_extends_existing(car: Car) -> None:
    """Calling with a larger N adds only new seats."""
    _bulk_create_seats(car, 3)
    assert car.seats.count() == 3

    _bulk_create_seats(car, 5)
    numbers = sorted(car.seats.values_list("number", flat=True))
    assert numbers == [1, 2, 3, 4, 5]
