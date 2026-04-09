from rest_framework import serializers

from .models import Booking, Order, Passenger


class PassengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Passenger
        fields = ["id", "name", "passport_number", "gender", "birth_date"]


class BookingSerializer(serializers.ModelSerializer):
    passenger = PassengerSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "departure",
            "seat",
            "station_from",
            "station_to",
            "passenger",
        ]


class OrderSerializer(serializers.ModelSerializer):
    bookings = BookingSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ["id", "created_at", "total_price", "features", "bookings"]
