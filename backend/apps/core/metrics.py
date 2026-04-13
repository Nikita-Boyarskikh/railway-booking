"""Prometheus business metrics for the railway-booking project.

Counters and histograms for key business operations. Exposed via
``/metrics`` by ``django-prometheus``.
"""

from prometheus_client import Counter, Histogram

orders_created = Counter(
    "bookings_orders_created_total",
    "Total orders successfully created",
)

bookings_created = Counter(
    "bookings_bookings_created_total",
    "Total individual seat bookings created",
)

order_conflict = Counter(
    "bookings_order_conflict_total",
    "Order creation failures due to seat conflict",
)

order_price_changed = Counter(
    "bookings_order_price_changed_total",
    "Order creation failures due to price mismatch",
)

order_total_price = Histogram(
    "bookings_order_total_price_usd",
    "Distribution of order total prices in USD",
    buckets=(50, 100, 250, 500, 1000, 2500, 5000, 10000),
)

search_departures_results = Histogram(
    "trains_search_departures_results",
    "Number of departures returned by search",
    buckets=(0, 1, 5, 10, 25, 50),
)
