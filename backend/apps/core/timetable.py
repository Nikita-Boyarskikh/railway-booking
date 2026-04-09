from datetime import datetime, timedelta
from decimal import Decimal


def compute_timetable(departure) -> list[dict]:
    """
    Return list of {station_id, station_name, arrival_time, departure_time}
    for each stop along the route, computed from train avg speed and stop durations.
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
    """
    Return (from_order, to_order) such that the segments with order in [from_order, to_order)
    cover the trip from station_from_id to station_to_id along route. None if not found.
    """
    rss = list(route.route_segments.select_related("segment").order_by("order"))
    from_order = None
    for rs in rss:
        if rs.segment.station_from_id == station_from_id:
            from_order = rs.order
            break
    if from_order is None:
        return None
    to_order = None
    for rs in rss:
        if rs.order >= from_order and rs.segment.station_to_id == station_to_id:
            to_order = rs.order + 1
            break
    if to_order is None:
        return None
    return from_order, to_order
