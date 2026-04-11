from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.trains.serializers import DepartureSearchQuerySerializer, SeatsQuerySerializer
from apps.trains.services import list_seats, search_departures


class DepartureSearchView(APIView):
    """``GET /api/departures/`` — search departures by ``from``/``to``/``date``."""

    def get(self, request: Request) -> Response:
        """Return matching departure summaries for the validated query."""
        query = DepartureSearchQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        return Response(search_departures(data["from_code"], data["to_code"], data["date"]))


class DepartureSeatsView(APIView):
    """``GET /api/departures/{uuid}/seats/`` — seats grouped by car with price/status."""

    def get(self, request: Request, uuid: str) -> Response:
        """Return seats for ``uuid`` restricted to the requested segment range."""
        query = SeatsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        return Response(list_seats(uuid, data["from_code"], data["to_code"]))
