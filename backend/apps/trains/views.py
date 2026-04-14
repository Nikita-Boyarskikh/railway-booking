from typing import TYPE_CHECKING

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.exceptions import DepartureNotFoundError
from apps.routes.exceptions import InvalidStationRangeError
from apps.stations.exceptions import InvalidStationCodeError
from apps.trains.serializers import DepartureSearchQuerySerializer, SeatsQuerySerializer
from apps.trains.services import get_departure, list_seats, search_departures

if TYPE_CHECKING:
    from rest_framework.request import Request


class DepartureSearchView(APIView):
    """``GET /api/v1/departures/`` — search departures by ``from``/``to``/``date``."""

    def get(self, request: Request) -> Response:
        """Return matching departure summaries for the validated query."""
        query = DepartureSearchQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        try:
            departures = search_departures(data["from_code"], data["to_code"], data["date"])
            return Response(departures)
        except InvalidStationCodeError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DepartureDetailView(APIView):
    """``GET /api/v1/departures/{uuid}/`` — summary for one departure restricted to ``from``/``to``."""

    def get(self, request: Request, uuid: str) -> Response:
        """Return the same shape as one row of ``DepartureSearchView`` for direct-link loads."""
        query = SeatsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        try:
            return Response(get_departure(uuid, data["from_code"], data["to_code"]))
        except DepartureNotFoundError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except (InvalidStationCodeError, InvalidStationRangeError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DepartureSeatsView(APIView):
    """``GET /api/v1/departures/{uuid}/seats/`` — seats grouped by car with price/status."""

    @method_decorator(ensure_csrf_cookie)
    def get(self, request: Request, uuid: str) -> Response:
        """Return seats for ``uuid`` restricted to the requested segment range."""
        query = SeatsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        try:
            return Response(list_seats(uuid, data["from_code"], data["to_code"]))
        except DepartureNotFoundError as e:
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except (InvalidStationCodeError, InvalidStationRangeError) as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
