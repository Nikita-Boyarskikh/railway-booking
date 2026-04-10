"""Pricing formulas for bookings.

The booking price for a segment range is::

    base_price + sum(segment.base_price for segments in range)
                 * route.price_factor * train.price_factor
                 * car.price_factor   * seat.price_factor

``base_price`` comes from ``constance.config.BASE_PRICE`` and is NOT
multiplied by any factor.
"""

from decimal import Decimal

from constance import config


def calc_segment_range_subtotal(route, from_order: int, to_order: int) -> Decimal:
    """Return ``sum(segment.base_price)`` for orders in ``[from_order, to_order)``.

    If ``route.route_segments`` has already been prefetched (together with the
    ``segment`` FK) the sum is computed in Python with no extra query.
    """
    # Use the prefetch cache if present (search_departures warms it);
    # otherwise fall back to a single ``select_related`` query.
    if "route_segments" in getattr(route, "_prefetched_objects_cache", {}):
        rss = route.route_segments.all()
    else:
        rss = route.route_segments.select_related("segment")
    return sum(
        (rs.segment.base_price for rs in rss if from_order <= rs.order < to_order),
        Decimal("0"),
    )


def calc_booking_price(route, train, car, seat, from_order: int, to_order: int) -> Decimal:
    """Return the final price for one seat over a segment range.

    Uses :func:`calc_segment_range_subtotal` then applies the route/train/car/
    seat price factors and adds the unmultiplied constance ``BASE_PRICE``.
    """
    subtotal = calc_segment_range_subtotal(route, from_order, to_order)
    multiplied = (
        subtotal
        * Decimal(route.price_factor)
        * Decimal(train.price_factor)
        * Decimal(car.price_factor)
        * Decimal(seat.price_factor)
    )
    return (Decimal(config.BASE_PRICE) + multiplied).quantize(Decimal("0.01"))
