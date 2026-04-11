from typing import Any

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.bookings.models import Booking, Gender, Order, Passenger


class PassengerSerializer(serializers.ModelSerializer[Passenger]):
    """Serializer for :class:`Passenger` embedded in booking output."""

    class Meta:
        model = Passenger
        fields = ["name", "passport_number", "gender", "birth_date"]


class BookingSerializer(serializers.ModelSerializer[Booking]):
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


class OrderItemSerializer(serializers.Serializer[None]):
    """Serializer for each item in the ``items`` list when creating an order."""

    car_number = serializers.IntegerField(min_value=1)
    seat_number = serializers.IntegerField(min_value=1)
    passenger_name = serializers.CharField(max_length=255)
    passenger_passport = serializers.CharField(max_length=64)
    passenger_gender = serializers.ChoiceField(choices=Gender.choices)
    passenger_birth_date = serializers.DateField()


class CreateOrderSerializer(serializers.Serializer[None]):
    """Input serializer for order creation, validating the request body."""

    departure_uuid = serializers.UUIDField()
    station_from_code = serializers.CharField(max_length=16)
    station_to_code = serializers.CharField(max_length=16)
    items = serializers.ListField(child=OrderItemSerializer(), min_length=1)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs["station_from_code"] == attrs["station_to_code"]:
            raise ValidationError({"station_to_code": "Station_from and station_to must differ."})
        return attrs


class OrderSerializer(serializers.ModelSerializer[Order]):
    """Order with nested bookings, returned from create/retrieve endpoints."""

    bookings = BookingSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["uuid", "created_at", "total_price", "features", "bookings"]
