from rest_framework import serializers


class DepartureSearchQuerySerializer(serializers.Serializer):
    from_id = serializers.IntegerField()
    to_id = serializers.IntegerField()
    date = serializers.DateField()

    def to_internal_value(self, data):
        # Map "from"/"to" query params to from_id/to_id
        return super().to_internal_value(
            {
                "from_id": data.get("from"),
                "to_id": data.get("to"),
                "date": data.get("date"),
            }
        )


class SeatsQuerySerializer(serializers.Serializer):
    from_id = serializers.IntegerField()
    to_id = serializers.IntegerField()

    def to_internal_value(self, data):
        return super().to_internal_value(
            {
                "from_id": data.get("from"),
                "to_id": data.get("to"),
            }
        )
