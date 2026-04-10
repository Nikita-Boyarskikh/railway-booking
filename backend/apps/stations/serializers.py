from rest_framework import serializers

from .models import Station


class StationSerializer(serializers.ModelSerializer):
    """Public ``{name, code}`` station representation."""

    class Meta:
        model = Station
        fields = ["name", "code"]
