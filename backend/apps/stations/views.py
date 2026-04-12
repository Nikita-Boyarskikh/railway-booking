"""Station endpoints."""

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.stations.services import list_stations


class StationListView(APIView):
    """``GET /api/v1/stations/`` — list all stations alphabetically by name.

    The response is cached under ``stations:all`` and invalidated by signal
    whenever a :class:`Station` row changes. See ``apps.core.cache`` and
    ``apps.core.signals``.
    """

    def get(self, request: Request) -> Response:
        """Return cached ``[{name, code}, ...]`` sorted by name."""
        return Response(list_stations())
