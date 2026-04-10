from datetime import datetime, timedelta
from decimal import Decimal


def compute_timetable(departure) -> list[dict]:
    """Return stop list for ``departure``.

    Each entry is a ``{station_id, station_name, arrival_time, departure_time}``
    dict. Times are ISO strings truncated to minutes. Computed from the train's
    average speed and the per-segment stop durations defined on ``RouteSegment``.
    """
    train = departure.train
    route_segments = list(
        departure.train.route.route_segments.select_related(
            "segment__station_from", "segment__station_to"
        ).order_by("order")
    )
    speed = Decimal(train.avg_speed_kmh)

    base_dt = datetime.combine(departure.date, departure.departure_time)
    cursor = base_dt
    stops: list[dict] = []

    for i, rs in enumerate(route_segments):
        seg = rs.segment
        # before traversing this segment, station_from is a stop
        if i == 0:
            stops.append(
                {
                    "station_id": seg.station_from_id,
                    "station_name": seg.station_from.name,
                    "arrival_time": None,
                    "departure_time": cursor.isoformat(timespec="minutes"),
                }
            )
        # traverse
        travel_hours = Decimal(seg.distance_km) / speed
        cursor = cursor + timedelta(hours=float(travel_hours))
        arrival = cursor
        # next stop is station_to of this seg; check if there's a next segment for stop_duration
        next_rs = route_segments[i + 1] if i + 1 < len(route_segments) else None
        stop_dur = next_rs.stop_duration if next_rs else timedelta(0)
        cursor = cursor + (stop_dur or timedelta(0))
        stops.append(
            {
                "station_id": seg.station_to_id,
                "station_name": seg.station_to.name,
                "arrival_time": arrival.isoformat(timespec="minutes"),
                "departure_time": cursor.isoformat(timespec="minutes") if next_rs else None,
            }
        )
    return stops


def find_route_orders(route, station_from_id: int, station_to_id: int) -> tuple[int, int] | None:
    """Return ``(from_order, to_order)`` covering the trip, or ``None``.

    Thin wrapper around :func:`apps.core.availability.resolve_station_range`
    kept for backwards compatibility with older call sites.
    """
    from apps.core.availability import resolve_station_range

    return resolve_station_range(route, station_from_id, station_to_id)
