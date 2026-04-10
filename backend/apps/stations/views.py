"""Station endpoints."""

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.cache import cached_stations

from .models import Station


class StationListView(APIView):
    """``GET /api/stations/`` — list all stations alphabetically by name.

    The response is cached under ``stations:all`` and invalidated by signal
    whenever a :class:`Station` row changes. See ``apps.core.cache`` and
    ``apps.core.signals``.
    """

    def get(self, request):
        """Return cached ``[{name, code}, ...]`` sorted by name."""
        data = cached_stations(
            lambda: [{"name": s.name, "code": s.code} for s in Station.objects.order_by("name")]
        )
        return Response(data)
