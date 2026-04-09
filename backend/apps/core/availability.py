def booking_segment_range(booking) -> tuple[int, int]:
    """Resolve a Booking's (from_order, to_order) along its departure's train route."""
    from apps.core.timetable import find_route_orders

    route = booking.departure.train.route
    rng = find_route_orders(route, booking.station_from_id, booking.station_to_id)
    return rng if rng else (0, 0)


def seat_is_free(departure, seat_id: int, from_order: int, to_order: int) -> bool:
    """
    Check no existing Booking for (departure, seat) overlaps [from_order, to_order).
    Computed by resolving each existing booking's range via the route.
    """
    from apps.bookings.models import Booking

    existing = Booking.objects.filter(departure=departure, seat_id=seat_id).select_related(
        "departure__train__route"
    )
    for b in existing:
        b_from, b_to = booking_segment_range(b)
        if b_from < to_order and from_order < b_to:
            return False
    return True


def free_seat_ids(departure, from_order: int, to_order: int) -> set[int]:
    """Return set of seat IDs that are free for the given range on this departure."""
    from apps.bookings.models import Booking
    from apps.trains.models import Seat

    all_seat_ids = set(Seat.objects.filter(car__train=departure.train).values_list("id", flat=True))
    occupied: set[int] = set()
    bookings = Booking.objects.filter(departure=departure).select_related("departure__train__route")
    for b in bookings:
        b_from, b_to = booking_segment_range(b)
        if b_from < to_order and from_order < b_to:
            occupied.add(b.seat_id)
    return all_seat_ids - occupied
