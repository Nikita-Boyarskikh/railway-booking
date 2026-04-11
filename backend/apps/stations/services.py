from apps.core.cache import StationsCache
from apps.core.types import StationDict
from apps.stations.models import Station
from apps.stations.serializers import StationSerializer


@StationsCache.wrap
def list_stations() -> list[StationDict]:
    """Return the list of all stations as ``[{name, code}, ...]`` sorted by name."""
    # drf serializers with many=True typing is very broken, so ignore the return value type check here
    return StationSerializer(Station.objects.order_by("name"), many=True).data # type: ignore[return-value]


def resolve_station_codes(from_code: str, to_code: str) -> tuple[Station | None, Station | None]:
    """Return ``(from_id, to_id)`` for two station codes, or ``None``."""
    stations = {s.code: s for s in Station.objects.filter(code__in=[from_code, to_code])}
    f = stations.get(from_code)
    t = stations.get(to_code)
    return f, t
