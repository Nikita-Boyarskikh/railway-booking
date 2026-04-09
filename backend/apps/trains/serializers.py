from rest_framework import serializers


class DepartureSearchQuerySerializer(serializers.Serializer):
    from_code = serializers.CharField()
    to_code = serializers.CharField()
    date = serializers.DateField()

    def to_internal_value(self, data):
        return super().to_internal_value(
            {
                "from_code": data.get("from"),
                "to_code": data.get("to"),
                "date": data.get("date"),
            }
        )


class SeatsQuerySerializer(serializers.Serializer):
    from_code = serializers.CharField()
    to_code = serializers.CharField()

    def to_internal_value(self, data):
        return super().to_internal_value(
            {
                "from_code": data.get("from"),
                "to_code": data.get("to"),
            }
        )