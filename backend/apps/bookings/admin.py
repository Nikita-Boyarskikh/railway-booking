from django.contrib import admin

from .models import Booking, Order, Passenger


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin[Order]):
    """Admin for :class:`Order`"""
    list_display = ("uuid", "created_at", "total_price")
    ordering = ("-created_at",)
    search_fields = ("uuid",)
    date_hierarchy = "created_at"


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin[Passenger]):
    """Admin for :class:`Passenger`"""
    list_display = ("name", "passport_number", "birth_date", "gender")
    search_fields = ("name", "passport_number")
    ordering = ("passport_number",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin[Booking]):
    """Admin for :class:`Booking`"""

    list_display = ("order__uuid", "departure", "seat", "station_from", "station_to", "passenger")
    search_fields = (
        "order__uuid",
        "departure__train__number",
        "departure__train__name",
        "passenger__name",
        "passenger__passport_number",
        "station_from__name",
        "station_from__code",
        "station_to__name",
        "station_to__code",
    )
    ordering = ("-order__created_at", "passenger__name")
    date_hierarchy = "departure__date"
