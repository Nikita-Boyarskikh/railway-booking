"""Service layer for the trains app.

Covers departure search and seat listing. Keeps all business logic out of
views and serializers so it can be tested and reused.
"""

from datetime import date as date_cls
from decimal import Decimal

from apps.core.availability import free_seat_ids, resolve_station_range
from apps.core.cache import cached_list_seats, cached_search_departures
from apps.core.pricing import calc_booking_price, calc_segment_range_subtotal
from apps.core.timetable import compute_timetable
from apps.core.types import CarDict, DepartureSummary, SeatDict, SeatsResponse
from apps.stations.models import Station

from .models import Departure


def _resolve_codes(from_code: str, to_code: str) -> tuple[int, int] | None:
    """Return ``(from_id, to_id)`` for two station codes, or ``None``."""
    stations = {s.code: s for s in Station.objects.filter(code__in=[from_code, to_code])}
    f = stations.get(from_code)
    t = stations.get(to_code)
    if not f or not t:
        return None
    return f.id, t.id


def search_departures(from_code: str, to_code: str, on_date: date_cls) -> list[DepartureSummary]:
    """Return departure summaries serving ``from_code``→``to_code`` on a date.

    Cached under ``search:{from}:{to}:{date}`` for a short TTL (see
    :mod:`apps.core.cache`); free-seat counts may be stale by up to the TTL.
    """
    return cached_search_departures(
        from_code,
        to_code,
        on_date.isoformat(),
        loader=lambda: _search_departures(from_code, to_code, on_date),
    )


def _search_departures(from_code: str, to_code: str, on_date: date_cls) -> list[DepartureSummary]:
    """Uncached implementation of :func:`search_departures`."""
    resolved = _resolve_codes(from_code, to_code)
    if not resolved:
        return []
    from_id, to_id = resolved

    results: list[DepartureSummary] = []
    qs = (
        Departure.objects.filter(date=on_date)
        .select_related("train__route")
        .prefetch_related(
            "train__route__route_segments__segment__station_from",
            "train__route__route_segments__segment__station_to",
            "train__cars__seats",
        )
    )
    for dep in qs:
        route = dep.train.route
        rng = resolve_station_range(route, from_id, to_id)
        if not rng:
            continue
        from_order, to_order = rng

        timetable = compute_timetable(dep)
        dep_at_a = next(
            (s["departure_time"] for s in timetable if s["station_id"] == from_id), None
        )
        arr_at_b = next((s["arrival_time"] for s in timetable if s["station_id"] == to_id), None)

        free_ids = free_seat_ids(dep, from_order, to_order)
        free_count = len(free_ids)

        subtotal = calc_segment_range_subtotal(route, from_order, to_order)

        min_price: Decimal | None = None
        for car in dep.train.cars.all():
            for seat in car.seats.all():
                if seat.id not in free_ids:
                    continue
                p = calc_booking_price(subtotal, seat)
                if min_price is None or p < min_price:
                    min_price = p

        results.append(
            {
                "uuid": str(dep.uuid),
                "train_number": dep.train.number,
                "train_name": dep.train.name,
                "departure_time": dep_at_a,
                "arrival_time": arr_at_b,
                "free_seat_count": free_count,
                "min_price": str(min_price) if min_price is not None else None,
            }
        )
    return results


def list_seats(departure: Departure, from_code: str, to_code: str) -> SeatsResponse:
    """Return seats for ``departure`` grouped by car with per-seat price/status.

    Response cached per ``(departure_uuid, from, to, generation)`` — bookings
    bump the generation so cached entries orphan immediately. See
    :mod:`apps.core.cache`.
    """
    return cached_list_seats(
        str(departure.uuid),
        from_code,
        to_code,
        loader=lambda: _list_seats(departure, from_code, to_code),
    )


def _list_seats(departure: Departure, from_code: str, to_code: str) -> SeatsResponse:
    """Uncached implementation of :func:`list_seats`."""
    resolved = _resolve_codes(from_code, to_code)
    if not resolved:
        return {"cars": []}
    from_id, to_id = resolved

    route = departure.train.route
    rng = resolve_station_range(route, from_id, to_id)
    if not rng:
        return {"cars": []}
    from_order, to_order = rng

    free_ids = free_seat_ids(departure, from_order, to_order)

    subtotal = calc_segment_range_subtotal(route, from_order, to_order)

    cars_out: list[CarDict] = []
    for car in departure.train.cars.all().prefetch_related("seats"):
        seats_out: list[SeatDict] = []
        for seat in car.seats.all():
            price = calc_booking_price(subtotal, seat)
            seats_out.append(
                SeatDict(
                    number=seat.number,
                    seat_type=seat.seat_type,
                    status="free" if seat.id in free_ids else "occupied",
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
