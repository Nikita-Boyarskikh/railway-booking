from datetime import date as date_cls
from decimal import Decimal

from apps.core.availability import free_seat_ids
from apps.core.pricing import calc_booking_price
from apps.core.timetable import compute_timetable, find_route_orders

from .models import Departure


def search_departures(from_id: int, to_id: int, on_date: date_cls) -> list[dict]:
    results: list[dict] = []
    qs = Departure.objects.filter(date=on_date).select_related("train__route")
    for dep in qs:
        route = dep.train.route
        rng = find_route_orders(route, from_id, to_id)
        if not rng:
            continue
        from_order, to_order = rng

        timetable = compute_timetable(dep)
        # find stop entries for from/to stations
        dep_at_a = next(
            (s["departure_time"] for s in timetable if s["station_id"] == from_id), None
        )
        arr_at_b = next((s["arrival_time"] for s in timetable if s["station_id"] == to_id), None)

        free_ids = free_seat_ids(dep, from_order, to_order)
        free_count = len(free_ids)

        # Compute min price across all seats (factors vary per car/seat)
        min_price: Decimal | None = None
        from .models import Seat as SeatModel

        seats = SeatModel.objects.filter(id__in=free_ids).select_related("car__train__route")
        for s in seats:
            p = calc_booking_price(route, dep.train, s.car, s, from_order, to_order)
            if min_price is None or p < min_price:
                min_price = p

        results.append(
            {
                "departure_id": dep.id,
                "train_number": dep.train.number,
                "train_name": dep.train.name,
                "departure_time": dep_at_a,
                "arrival_time": arr_at_b,
                "free_seat_count": free_count,
                "min_price": str(min_price) if min_price is not None else None,
            }
        )
    return results


def list_seats(departure: Departure, from_id: int, to_id: int) -> dict:
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
                    "id": seat.id,
                    "number": seat.number,
                    "seat_type": seat.seat_type,
                    "status": "free" if seat.id in free_ids else "occupied",
                    "price": str(price),
                }
            )
        cars_out.append(
            {
                "id": car.id,
                "number": car.number,
                "car_type": car.car_type,
                "features": car.features,
                "seats": seats_out,
            }
        )
    return {"cars": cars_out}
