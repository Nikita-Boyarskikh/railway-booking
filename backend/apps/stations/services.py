from apps.core.cache import StationsCache
from apps.stations.exceptions import InvalidStationCodeError
from apps.stations.models import Station


@StationsCache.wrap
def list_stations() -> list[Station]:
    """Return the list of all stations as ``[{name, code}, ...]`` sorted by name."""
    return list(Station.objects.order_by("name"))


def resolve_station_codes(from_code: str, to_code: str) -> tuple[Station, Station]:
    """
    Return ``(from_id, to_id)`` for two station codes.
    If either code is invalid, raise :class:`
    Note that this function does not check that the stations are on the same route.
    That is the responsibility of the caller (e.g. in :func:`list_departures`).
    """
    stations = {s.code: s for s in Station.objects.filter(code__in=[from_code, to_code])}
    from_station = stations.get(from_code)
    to_station = stations.get(to_code)
    if not from_station:
        raise InvalidStationCodeError(from_code)
    if not to_station:
        raise InvalidStationCodeError(to_code)
    return from_station, to_station
