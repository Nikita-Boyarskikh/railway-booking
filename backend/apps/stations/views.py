from rest_framework import generics

from .models import Station
from .serializers import StationSerializer


class StationListView(generics.ListAPIView):
    """``GET /api/stations/`` — list all stations alphabetically by name."""

    queryset = Station.objects.all().order_by("name")
    serializer_class = StationSerializer
