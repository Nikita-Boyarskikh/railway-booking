"""Pricing formulas for bookings.

The booking price for a segment range is::

    base_price + sum(connection.base_price for segments in range)
                 * route.price_factor * train.price_factor
                 * car.price_factor   * seat.price_factor

``base_price`` comes from ``constance.config.BASE_PRICE`` and is NOT
multiplied by any factor.
"""

from django.conf import settings
from djmoney.money import Money

from apps.routes.models import Route
from apps.routes.services import get_route_segments
from apps.trains.models import Seat


def calc_segment_range_subtotal(route: Route, from_order: int, to_order: int) -> Money:
    """
    Return ``sum(connection.base_price)`` for orders in ``[from_order, to_order)``.

    Uses prefetched ``route_segments`` if available to avoid extra DB queries.
    The base price is the only component of the booking price that depends on
    the segment range, so this function is separate from :func:`calc_booking_price`.
    This allows caching the subtotal for a route and segment range independently
    of the seat/booking-specific factors applied in :func:`calc_booking_price`.
    """
    return sum(
        (
            route_segment.connection.base_price
            for route_segment in get_route_segments(route)
            if from_order <= route_segment.order < to_order
        ),
        Money(currency=settings.DEFAULT_CURRENCY),
    )


def calc_booking_price(base_price: Money, subtotal: Money, seat: Seat) -> Money:
    """Return the final price for one seat on a booking with a given segment range subtotal.

    NOTE: Use :func:`calc_segment_range_subtotal` to get subtotal from a route and segment range.
     This function only applies the route/train/car/seat price factors
     and adds the unmultiplied constance ``BASE_PRICE``.
    """
    multiplied = (
        subtotal
        * seat.car.train.route.price_factor
        * seat.car.train.price_factor
        * seat.car.price_factor
        * seat.price_factor
    )
    return base_price + multiplied
