from typing import Any

from rest_framework import serializers

from apps.trains.models import Departure, Seat


class DepartureSearchQuerySerializer(serializers.Serializer[Departure]):
    """Query-string validator for the departure-search endpoint."""

    from_code = serializers.CharField()
    to_code = serializers.CharField()
    date = serializers.DateField()

    def to_internal_value(self, data: Any) -> Any:
        """Remap public ``from``/``to`` params to internal field names."""
        return super().to_internal_value(
            {
                "from_code": data.get("from"),
                "to_code": data.get("to"),
                "date": data.get("date"),
            }
        )


class SeatsQuerySerializer(serializers.Serializer[Seat]):
    """Query-string validator for the seat-listing endpoint."""

    from_code = serializers.CharField()
    to_code = serializers.CharField()

    def to_internal_value(self, data: Any) -> Any:
        """Remap public ``from``/``to`` params to internal field names."""
        return super().to_internal_value(
            {
                "from_code": data.get("from"),
                "to_code": data.get("to"),
            }
        )
