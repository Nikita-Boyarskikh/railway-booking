"""Service layer for the trains' app.

Covers departure search and seat listing. Keeps all business logic out of
views and serializers so it can be tested and reused.
"""

import datetime
from functools import cache
from uuid import UUID

from constance import config
from django.conf import settings
from django.db.models import QuerySet
from djmoney.money import Money
from rest_framework.generics import get_object_or_404

from apps.core.availability import free_seat_ids
from apps.core.cache import SearchCache, SeatsCache
from apps.core.pricing import calc_booking_price, calc_segment_range_subtotal
from apps.core.timetable import compute_timetable
from apps.core.types import CarDict, DepartureSummary, SeatDict, SeatsResponse, SeatStatus
from apps.routes.exceptions import InvalidStationRangeError
from apps.routes.services import resolve_station_range
from apps.stations.services import resolve_station_codes
from apps.trains.models import Departure


def _select_related_for_departure_qs(qs: QuerySet[Departure]) -> QuerySet[Departure]:
    """Apply the necessary select_related and prefetch_related calls to a Departure queryset."""
    return qs.select_related("train__route").prefetch_related(
        "train__route__route_segments__segment",
        "train__cars__seats",
    )


@SearchCache.wrap
def search_departures(
    from_code: str, to_code: str, on_date: datetime.date
) -> list[DepartureSummary]:
    """
    Return departure summaries serving ``from_code``→``to_code`` on a date.

    Raises:
        InvalidStationCodeError: On unknown references or route mismatch.
    """
    from_station, to_station = resolve_station_codes(from_code, to_code)

    # Multiple departures share a route, so cache the (route, from, to) subtotal
    # across the loop rather than recomputing it per departure.
    # The free seat IDs are also cached per departure and station range.
    get_segment_range_subtotal = cache(calc_segment_range_subtotal)
    base_price = Money(config.BASE_PRICE, DEFAULT_CURRENCY)

    results: list[DepartureSummary] = []
    for departure in _select_related_for_departure_qs(Departure.objects.filter(date=on_date)):
        route = departure.train.route

        try:
            from_order, to_order = resolve_station_range(route, from_station.pk, to_station.pk)
        except InvalidStationRangeError:
            continue

        timetable = compute_timetable(departure)
        dep_at_a = next(
            (s["departure_time"] for s in timetable if s["station_id"] == from_station.pk), None
        )
        arr_at_b = next(
            (s["arrival_time"] for s in timetable if s["station_id"] == to_station.pk), None
        )

        free_ids = free_seat_ids(departure, from_order, to_order)
        free_count = len(free_ids)

        subtotal = get_segment_range_subtotal(route, from_order, to_order)

        min_price: Money | None = None
        for car in departure.train.cars.all():
            for seat in car.seats.all():
                if seat.pk not in free_ids:
                    continue
                p = calc_booking_price(base_price, subtotal, seat)
                if min_price is None or p < min_price:
                    min_price = p

        results.append(
            {
                "uuid": str(departure.uuid),
                "train_number": departure.train.number,
                "train_name": departure.train.name,
                "departure_time": dep_at_a,
                "arrival_time": arr_at_b,
                "free_seat_count": free_count,
                "min_price": str(min_price) if min_price is not None else None,
            }
        )
    return results


@SeatsCache.wrap
def list_seats(departure_uuid: UUID | str, from_code: str, to_code: str) -> SeatsResponse:
    """Return seats for ``departure`` grouped by car with per-seat price/status."""
    departure = get_object_or_404(
        _select_related_for_departure_qs(Departure.objects.all()),
        uuid=departure_uuid,
    )

    from_station, to_station = resolve_station_codes(from_code, to_code)

    route = departure.train.route
    from_order, to_order = resolve_station_range(route, from_station.pk, to_station.pk)

    free_ids = free_seat_ids(departure, from_order, to_order)
    base_price = Money(config.BASE_PRICE, settings.DEFAULT_CURRENCY)
    subtotal = calc_segment_range_subtotal(route, from_order, to_order)

    cars_out: list[CarDict] = []
    for car in departure.train.cars.all():
        seats_out: list[SeatDict] = []
        for seat in car.seats.all():
            price = calc_booking_price(base_price, subtotal, seat)
            seats_out.append(
                SeatDict(
                    number=seat.number,
                    seat_type=seat.seat_type,
                    status=SeatStatus.FREE if seat.pk in free_ids else SeatStatus.OCCUPIED,
                    price=str(price),
                )
            )
        cars_out.append(
            CarDict(
                number=car.number,
                car_type=car.car_type,
                features=car.features,
                seats=seats_out,
            )
        )
    return SeatsResponse(cars=cars_out)
