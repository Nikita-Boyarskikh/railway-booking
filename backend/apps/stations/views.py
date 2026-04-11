"""Station endpoints."""

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.cache import cached_stations

from .models import Station
from .serializers import StationSerializer


class StationListView(APIView):
    """``GET /api/stations/`` — list all stations alphabetically by name.

    The response is cached under ``stations:all`` and invalidated by signal
    whenever a :class:`Station` row changes. See ``apps.core.cache`` and
    ``apps.core.signals``.
    """

    def get(self, request: Request) -> Response:
        """Return cached ``[{name, code}, ...]`` sorted by name."""
        data = cached_stations(
            # drf many=True serializers return lists, so this is type-compatible with the cache loader
            lambda: StationSerializer(Station.objects.order_by("name"), many=True).data  # type: ignore[arg-type,return-value]
        )
        return Response(data)
