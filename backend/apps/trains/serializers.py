from typing import Any

from rest_framework import serializers

from apps.trains.models import Departure, Seat


def _remap_from_to(data: dict[str, Any]) -> dict[str, Any]:
    """Remap public ``from``/``to`` params to internal ``from_code``/``to_code``."""
    return {
        "from_code": data.get("from"),
        "to_code": data.get("to"),
    }


class DepartureSearchQuerySerializer(serializers.Serializer[Departure]):
    """Query-string validator for the departure-search endpoint."""

    from_code = serializers.CharField()
    to_code = serializers.CharField()
    date = serializers.DateField()

    def to_internal_value(self, data: Any) -> Any:
        return super().to_internal_value(
            {
                "date": data.get("date"),
                **_remap_from_to(data),
            }
        )


class SeatsQuerySerializer(serializers.Serializer[Seat]):
    """Query-string validator for the seat-listing and departure-detail endpoints."""

    from_code = serializers.CharField()
    to_code = serializers.CharField()

    def to_internal_value(self, data: Any) -> Any:
        return super().to_internal_value(_remap_from_to(data))
