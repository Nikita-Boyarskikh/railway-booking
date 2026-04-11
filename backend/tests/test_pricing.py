from decimal import Decimal

import pytest
from moneyed import Money

from apps.core.pricing import calc_booking_price, calc_segment_range_subtotal
from apps.routes.models import Route
from apps.trains.models import Car, Seat


@pytest.mark.django_db
@pytest.mark.usefixtures("base_price")
@pytest.mark.parametrize(
    ("from_order", "to_order", "route_factor", "car_factor", "seat_factor", "expected"),
    [
        # full route, all factors 1.0: base 100 + segments (200+300+400) = 1000
        (0, 3, "1", "1", "1", "1000.00"),
        # partial route 0..1: base 100 + segment 200 = 300
        (0, 1, "1", "1", "1", "300.00"),
        # route_factor applies to segments only: 200*2 + 100 = 500
        (0, 1, "2", "1", "1", "500.00"),
        # seat_factor: 200*1.5 + 100 = 400
        (0, 1, "1", "1", "1.5", "400.00"),
        # car_factor: 200*1.5 + 100 = 400
        (0, 1, "1", "1.5", "1", "400.00"),
        # all factors combined: 200 * 2 * 1.5 * 1.5 + 100 = 1000
        (0, 1, "2", "1.5", "1.5", "1000.00"),
        # middle segment only (1..2 = BC = 300): 300 + 100 = 400
        (1, 2, "1", "1", "1", "400.00"),
    ],
    ids=[
        "full_route",
        "partial_AB",
        "route_factor_2x",
        "seat_factor_1.5x",
        "car_factor_1.5x",
        "all_factors_combined",
        "middle_segment_BC",
    ],
)
def test_pricing(
    route: Route,
    car: Car,
    seat: Seat,
    from_order: int,
    to_order: int,
    route_factor: str,
    car_factor: str,
    seat_factor: str,
    expected: str,
) -> None:
    route.price_factor = Decimal(route_factor)
    route.save()
    car.price_factor = Decimal(car_factor)
    car.save()
    seat.price_factor = Decimal(seat_factor)
    seat.save()
    seat.car = car  # refresh cached relation
    subtotal = calc_segment_range_subtotal(route, from_order, to_order)
    price = calc_booking_price(subtotal, seat)
    assert price == Money(expected, "USD")
