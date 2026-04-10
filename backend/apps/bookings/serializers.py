from rest_framework import serializers

from .models import Booking, Order, Passenger


class PassengerSerializer(serializers.ModelSerializer):
    """Serializer for :class:`Passenger` embedded in booking output."""

    class Meta:
        model = Passenger
        fields = ["name", "passport_number", "gender", "birth_date"]


class BookingSerializer(serializers.ModelSerializer):
    """Public booking representation using ``uuid``/``code``/``(car, seat)`` ids."""

    passenger = PassengerSerializer(read_only=True)
    departure_uuid = serializers.UUIDField(source="departure.uuid", read_only=True)
    car_number = serializers.IntegerField(source="seat.car.number", read_only=True)
    seat_number = serializers.IntegerField(source="seat.number", read_only=True)
    station_from_code = serializers.CharField(source="station_from.code", read_only=True)
    station_to_code = serializers.CharField(source="station_to.code", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "departure_uuid",
            "car_number",
            "seat_number",
            "station_from_code",
            "station_to_code",
            "passenger",
        ]


class OrderSerializer(serializers.ModelSerializer):
    """Order with nested bookings, returned from create/retrieve endpoints."""

    bookings = BookingSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["uuid", "created_at", "total_price", "features", "bookings"]
