from datetime import datetime, timedelta

from apps.core.db_utils import use_prefetched_if_available
from apps.trains.models import Departure

from .types import TimetableStop


def compute_timetable(departure: Departure) -> list[TimetableStop]:
    """Return stop list for ``departure``.

    Each entry is a ``{station_id, arrival_time, departure_time}``
    dict. Times are ISO strings truncated to minutes. Computed from the train's
    average speed and the per-segment stop durations defined on ``RouteSegment``.

    Uses prefetched ``route_segments`` if available so that callers iterating
    over many departures (e.g. ``_search_departures``) do not issue N+1 queries.
    """
    route = departure.train.route
    route_segments = list(
        use_prefetched_if_available(
            route,
            "route_segments",
            lambda qs: qs.select_related("segment__station_from", "segment__station_to").order_by(
                "order"
            ),
        )
    )

    cursor = datetime.combine(departure.date, departure.departure_time)
    stops: list[TimetableStop] = []

    for i, route_segment in enumerate(route_segments):
        segment = route_segment.segment
        # before traversing this segment, station_from is a stop
        if i == 0:
            stops.append(
                {
                    "station_id": segment.station_from_id,
                    "arrival_time": None,
                    "departure_time": cursor.isoformat(timespec="minutes"),
                }
            )

        # traverse
        travel_hours = segment.distance_km / departure.train.avg_speed_kmh
        cursor += timedelta(hours=travel_hours)
        arrival = cursor
        cursor += route_segment.stop_duration
        stops.append(
            {
                "station_id": segment.station_to_id,
                "arrival_time": arrival.isoformat(timespec="minutes"),
                "departure_time": cursor.isoformat(timespec="minutes"),
            }
        )
    return stops
