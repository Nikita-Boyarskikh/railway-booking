from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from djmoney.money import Money

from apps.core.pricing import calc_booking_price, calc_segment_range_subtotal

if TYPE_CHECKING:
    from apps.trains.models import Seat


@pytest.mark.django_db
@pytest.mark.parametrize(
    (
        "from_order",
        "to_order",
        "route_factor",
        "train_factor",
        "car_factor",
        "seat_factor",
        "expected",
    ),
    [
        # full route, all factors 1.0: base 100 + segments (200+300+400) = 1000
        (0, 3, "1", "1", "1", "1", "1000.00"),
        # partial route 0..1: base 100 + segment 200 = 300
        (0, 1, "1", "1", "1", "1", "300.00"),
        # route_factor applies to segments only: 200*2 + 100 = 500
        (0, 1, "2", "1", "1", "1", "500.00"),
        # seat_factor: 200*1.5 + 100 = 400
        (0, 1, "1", "1", "1", "1.5", "400.00"),
        # car_factor: 200*1.5 + 100 = 400
        (0, 1, "1", "1", "1.5", "1", "400.00"),
        # train_factor: 200*1.5 + 100 = 400
        (0, 1, "1", "1.5", "1", "1", "400.00"),
        # all factors combined: 200 * 2 * 1.1 * 1.5 * 1.5 + 100 = 1090
        (0, 1, "2", "1.1", "1.5", "1.5", "1090.00"),
        # middle segment only (1..2 = BC = 300): 300 + 100 = 400
        (1, 2, "1", "1", "1", "1", "400.00"),
    ],
    ids=[
        "full_route",
        "partial_AB",
        "route_factor_2x",
        "seat_factor_1.5x",
        "car_factor_1.5x",
        "train_factor_1.5x",
        "all_factors_combined",
        "middle_segment_BC",
    ],
)
def test_pricing(
    seat: Seat,
    from_order: int,
    to_order: int,
    route_factor: str,
    train_factor: str,
    car_factor: str,
    seat_factor: str,
    expected: str,
) -> None:
    seat.car.train.route.price_factor = Decimal(route_factor)
    seat.car.train.route.save()
    seat.car.train.price_factor = Decimal(train_factor)
    seat.car.train.save()
    seat.car.price_factor = Decimal(car_factor)
    seat.car.save()
    seat.price_factor = Decimal(seat_factor)
    seat.save()

    subtotal = calc_segment_range_subtotal(seat.car.train.route, from_order, to_order)
    base_price = Money(100, "USD")
    price = calc_booking_price(base_price, subtotal, seat)
    assert price == Money(expected, "USD")
