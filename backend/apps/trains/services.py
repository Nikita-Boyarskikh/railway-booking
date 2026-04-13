"""Service layer for the trains' app.

Covers departure search and seat listing. Keeps all business logic out of
views and serializers so it can be tested and reused.
"""

import logging
from typing import TYPE_CHECKING

from constance import config
from django.conf import settings
from djmoney.money import Money

from apps.bookings.exceptions import DepartureNotFoundError
from apps.core.availability import batch_occupied_seat_ids_with_subtotal, free_seat_ids
from apps.core.cache import SearchCache, SeatsCache
from apps.core.metrics import search_departures_results
from apps.core.pricing import calc_booking_price, calc_segment_range_subtotal
from apps.core.timetable import compute_timetable
from apps.core.types import CarDict, DepartureSummary, SeatDict, SeatsResponse, SeatStatus
from apps.routes.services import resolve_station_range
from apps.stations.services import resolve_station_codes
from apps.trains.models import Departure

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import datetime
    from uuid import UUID


@SearchCache.wrap
def search_departures(
    from_code: str, to_code: str, on_date: datetime.date
) -> list[DepartureSummary]:
    """
    Return departure summaries serving ``from_code``→``to_code`` on a date.

    Departures whose route does not pass through both stations are excluded
    at the SQL level so we never load irrelevant rows. Occupied-seat
    lookups are batched into a single query across all matching departures.

    Raises:
        InvalidStationCodeError: On unknown references or route mismatch.
    """
    from_station, to_station = resolve_station_codes(from_code, to_code)
    # Two separate .filter() calls so each condition can match a *different*
    # route segment — a single .filter() would require one segment to have
    # both station_from=A and station_to=D (only a direct connection).
    departures = list(
        Departure.objects.filter(
            date=on_date,
            train__route__route_segments__connection__station_from=from_station,
        )
        .filter(train__route__route_segments__connection__station_to=to_station)
        .distinct()
        .with_route()
        .with_seats()
    )
    if not departures:
        return []

    occupied_with_subtotal_by_departure = batch_occupied_seat_ids_with_subtotal(
        departures, from_station.pk, to_station.pk
    )
    base_price = Money(config.BASE_PRICE, settings.DEFAULT_CURRENCY)

    results: list[DepartureSummary] = []
    for departure in departures:
        if (occupied := occupied_with_subtotal_by_departure.get(departure.pk)) is None:
            continue
        occupied_seats, subtotal = occupied

        timetable = compute_timetable(departure)
        dep_at_a = next(
            (s["departure_time"] for s in timetable if s["station_id"] == from_station.pk), None
        )
        arr_at_b = next(
            (s["arrival_time"] for s in timetable if s["station_id"] == to_station.pk), None
        )

        # All seats for this departure (already prefetched).
        all_seat_ids = {seat.pk for car in departure.train.cars.all() for seat in car.seats.all()}
        free_ids = all_seat_ids - occupied_seats

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
                "free_seat_count": len(free_ids),
                "min_price": str(min_price) if min_price is not None else None,
            }
        )
    logger.info(
        "search_departures: %s→%s on %s found %d departures",
        from_code,
        to_code,
        on_date,
        len(results),
    )
    search_departures_results.observe(len(results))
    return results


@SeatsCache.wrap
def list_seats(departure_uuid: UUID | str, from_code: str, to_code: str) -> SeatsResponse:
    """Return seats for ``departure`` grouped by car with per-seat price/status."""
    try:
        departure = Departure.objects.with_route().with_seats().get(uuid=departure_uuid)
    except Departure.DoesNotExist as e:
        raise DepartureNotFoundError() from e

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
