from decimal import Decimal

import pytest
from moneyed import Money

from apps.core.pricing import calc_booking_price, calc_segment_range_subtotal
from tests.conftest import TypeTestData


@pytest.mark.django_db
def test_pricing_full_route(test_data: TypeTestData) -> None:
    d = test_data
    # full route 0..3, segments 200+300+400=900, all factors 1.0, base 100
    subtotal = calc_segment_range_subtotal(d["route"], 0, 3)
    price = calc_booking_price(subtotal, d["seat"])
    assert price == Money("1000.00", "USD")


@pytest.mark.django_db
def test_pricing_partial(test_data: TypeTestData) -> None:
    d = test_data
    # segments 0..1 → seg1 only = 200, + base 100
    subtotal = calc_segment_range_subtotal(d["route"], 0, 1)
    price = calc_booking_price(subtotal, d["seat"])
    assert price == Money("300.00", "USD")


@pytest.mark.django_db
def test_pricing_factors_apply_to_segments_not_base(test_data: TypeTestData) -> None:
    d = test_data
    d["route"].price_factor = Decimal("2.0")
    d["route"].save()
    # seg1 (200) * 2.0 = 400, + base 100 = 500
    subtotal = calc_segment_range_subtotal(d["route"], 0, 1)
    price = calc_booking_price(subtotal, d["seat"])
    assert price == Money("500.00", "USD")


@pytest.mark.django_db
def test_pricing_seat_factor(test_data: TypeTestData) -> None:
    d = test_data
    d["seat"].price_factor = Decimal("1.5")
    d["seat"].save()
    # seg1 (200) * 1.5 = 300, + base 100 = 400
    subtotal = calc_segment_range_subtotal(d["route"], 0, 1)
    price = calc_booking_price(subtotal, d["seat"])
    assert price == Money("400.00", "USD")
