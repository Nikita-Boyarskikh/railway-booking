from typing import TYPE_CHECKING

from apps.core.cache import StationsCache
from apps.stations.exceptions import InvalidStationCodeError
from apps.stations.models import Station
from apps.stations.serializers import StationSerializer

if TYPE_CHECKING:
    from apps.core.types import StationDict


@StationsCache.wrap
def list_stations() -> list[StationDict]:
    """Return the list of all stations as ``[{name, code}, ...]`` sorted by name."""
    return StationSerializer(Station.objects.order_by("name"), many=True).data  # type: ignore[return-value]


def resolve_station_codes(from_code: str, to_code: str) -> tuple[Station, Station]:
    """Return ``(from_station, to_station)`` for two station codes.

    Does not verify that both stations belong to the same route —
    that is the caller's responsibility.

    Raises:
        InvalidStationCodeError: If either code does not match a known station.
    """
    stations = {s.code: s for s in Station.objects.filter(code__in=[from_code, to_code])}
    from_station = stations.get(from_code)
    to_station = stations.get(to_code)
    if not from_station:
        raise InvalidStationCodeError(from_code)
    if not to_station:
        raise InvalidStationCodeError(to_code)
    return from_station, to_station
