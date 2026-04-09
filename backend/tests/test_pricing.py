from decimal import Decimal

import pytest

from apps.core.pricing import calc_booking_price


@pytest.mark.django_db
def test_pricing_full_route(demo_data):
    d = demo_data
    # full route 0..3, segments 200+300+400=900, all factors 1.0, base 100
    price = calc_booking_price(d["route"], d["train"], d["car"], d["seat"], 0, 3)
    assert price == Decimal("1000.00")


@pytest.mark.django_db
def test_pricing_partial(demo_data):
    d = demo_data
    # segments 0..1 → seg1 only = 200, + base 100
    price = calc_booking_price(d["route"], d["train"], d["car"], d["seat"], 0, 1)
    assert price == Decimal("300.00")


@pytest.mark.django_db
def test_pricing_factors_apply_to_segments_not_base(demo_data):
    d = demo_data
    d["route"].price_factor = Decimal("2.0")
    d["route"].save()
    # seg1 (200) * 2.0 = 400, + base 100 = 500
    price = calc_booking_price(d["route"], d["train"], d["car"], d["seat"], 0, 1)
    assert price == Decimal("500.00")
