from decimal import Decimal

from .models import Config


def calc_segment_range_subtotal(route, from_order: int, to_order: int) -> Decimal:
    """Sum of segment.base_price for route segments with order in [from_order, to_order)."""
    qs = route.route_segments.filter(order__gte=from_order, order__lt=to_order).select_related(
        "segment"
    )
    return sum((rs.segment.base_price for rs in qs), Decimal("0"))


def calc_booking_price(route, train, car, seat, from_order: int, to_order: int) -> Decimal:
    """
    booking_price = base_price + sum(seg.base_price) * route.pf * train.pf * car.pf * seat.pf
    base_price (config) is NOT multiplied.
    """
    cfg = Config.get()
    subtotal = calc_segment_range_subtotal(route, from_order, to_order)
    multiplied = (
        subtotal
        * Decimal(route.price_factor)
        * Decimal(train.price_factor)
        * Decimal(car.price_factor)
        * Decimal(seat.price_factor)
    )
    return (Decimal(cfg.base_price) + multiplied).quantize(Decimal("0.01"))
