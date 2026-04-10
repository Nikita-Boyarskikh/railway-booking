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
from django.db.models import QuerySet
from djmoney.money import Money

from apps.core.db_utils import use_prefetched_if_available
from apps.routes.models import Route, RouteSegment
from apps.trains.models import Seat
from config.settings import DEFAULT_CURRENCY


def calc_segment_range_subtotal(route: Route, from_order: int, to_order: int) -> Money:
    """
    Return ``sum(segment.base_price)`` for orders in ``[from_order, to_order)``.

    Uses prefetched ``route_segments`` if available to avoid extra DB queries.
    The base price is the only component of the booking price that depends on
    the segment range, so this function is separate from :func:`calc_booking_price`.
    This allows caching the subtotal for a route and segment range independently
    of the seat/booking-specific factors applied in :func:`calc_booking_price`.
    """
    rss: QuerySet[RouteSegment] = use_prefetched_if_available(
        route, "route_segments", lambda qs: qs.select_related("segment")
    )
    return sum(
        (rs.segment.base_price for rs in rss if from_order <= rs.order < to_order),
        Money(currency=DEFAULT_CURRENCY),
    )


def calc_booking_price(subtotal: Money, seat: Seat) -> Money:
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
    return Money(config.BASE_PRICE, currency=DEFAULT_CURRENCY) + multiplied
