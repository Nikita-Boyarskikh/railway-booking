from datetime import date as date_cls
from decimal import Decimal

from apps.core.availability import free_seat_ids
from apps.core.pricing import calc_booking_price
from apps.core.timetable import compute_timetable, find_route_orders
from apps.stations.models import Station

from .models import Departure


def _resolve_codes(from_code: str, to_code: str) -> tuple[int, int] | None:
    stations = {s.code: s for s in Station.objects.filter(code__in=[from_code, to_code])}
    f = stations.get(from_code)
    t = stations.get(to_code)
    if not f or not t:
        return None
    return f.id, t.id


def search_departures(from_code: str, to_code: str, on_date: date_cls) -> list[dict]:
    resolved = _resolve_codes(from_code, to_code)
    if not resolved:
        return []
    from_id, to_id = resolved

    results: list[dict] = []
    qs = Departure.objects.filter(date=on_date).select_related("train__route")
    for dep in qs:
        route = dep.train.route
        rng = find_route_orders(route, from_id, to_id)
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

        min_price: Decimal | None = None
        from .models import Seat as SeatModel

        seats = SeatModel.objects.filter(id__in=free_ids).select_related("car__train__route")
        for s in seats:
            p = calc_booking_price(route, dep.train, s.car, s, from_order, to_order)
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


def list_seats(departure: Departure, from_code: str, to_code: str) -> dict:
    resolved = _resolve_codes(from_code, to_code)
    if not resolved:
        return {"cars": []}
    from_id, to_id = resolved

    route = departure.train.route
    rng = find_route_orders(route, from_id, to_id)
    if not rng:
        return {"cars": []}
    from_order, to_order = rng

    free_ids = free_seat_ids(departure, from_order, to_order)

    cars_out = []
    for car in departure.train.cars.all().prefetch_related("seats"):
        seats_out = []
        for seat in car.seats.all():
            price = calc_booking_price(route, departure.train, car, seat, from_order, to_order)
            seats_out.append(
                {
                    "number": seat.number,
                    "seat_type": seat.seat_type,
                    "status": "free" if seat.id in free_ids else "occupied",
                    "price": str(price),
                }
            )
        cars_out.append(
            {
                "number": car.number,
                "car_type": car.car_type,
                "features": car.features,
                "seats": seats_out,
            }
        )
    return {"cars": cars_out}