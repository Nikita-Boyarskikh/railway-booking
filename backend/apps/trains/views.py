from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Departure
from .serializers import DepartureSearchQuerySerializer, SeatsQuerySerializer
from .services import list_seats, search_departures


class DepartureSearchView(APIView):
    """``GET /api/departures/`` — search departures by ``from``/``to``/``date``."""

    def get(self, request):
        """Return matching departure summaries for the validated query."""
        query = DepartureSearchQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        return Response(search_departures(data["from_code"], data["to_code"], data["date"]))


class DepartureSeatsView(APIView):
    """``GET /api/departures/{uuid}/seats/`` — seats grouped by car with price/status."""

    def get(self, request, uuid):
        """Return seats for ``uuid`` restricted to the requested segment range."""
        query = SeatsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        departure = get_object_or_404(Departure.objects.select_related("train__route"), uuid=uuid)
        return Response(list_seats(departure, data["from_code"], data["to_code"]))
