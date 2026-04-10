"""Django admin registrations for the trains app."""
from typing import Any

from django import forms
from django.contrib import admin
from django.http import HttpRequest

from .models import Car, Departure, Seat, Train


class CarInline(admin.TabularInline[Car, Train]):
    """Inline editor for a train's cars on the train change page."""

    model = Car
    extra = 0
    show_change_link = True
    fields = ("number", "car_type", "price_factor")


@admin.register(Train)
class TrainAdmin(admin.ModelAdmin[Train]):
    """Admin for :class:`Train` with an inline list of cars."""

    inlines = [CarInline]
    list_display = ("number", "name", "route")


class SeatInline(admin.TabularInline[Seat, Car]):
    """Inline editor for a car's seats on the car change page."""

    model = Seat
    extra = 0
    fields = ("number", "seat_type", "price_factor")


class CarAdminForm(forms.ModelForm[Car]):
    """Form for :class:`Car` with a bulk seat-creation helper."""

    seats_to_create = forms.IntegerField(
        required=False,
        min_value=0,
        help_text="Bulk-create N seats numbered 1..N, skipping existing",
    )

    class Meta:
        model = Car
        fields = ("train", "number", "car_type", "features", "price_factor")


@admin.register(Car)
class CarAdmin(admin.ModelAdmin[Car]):
    """Admin for :class:`Car` with inline seats and optional bulk creation."""

    form = CarAdminForm
    inlines = [SeatInline]
    list_display = ("number", "train", "car_type", "price_factor")

    def save_model(self, request: HttpRequest, obj: Car, form: Any, change: Any) -> None:
        """Save the car and optionally bulk-create seats numbered ``1..N``.

        Skips seat numbers that already exist on the car via
        ``bulk_create(..., ignore_conflicts=True)``.
        """
        super().save_model(request, obj, form, change)
        n = form.cleaned_data.get("seats_to_create") or 0
        if n > 0:
            existing = set(obj.seats.values_list("number", flat=True))
            new_seats = [
                Seat(car=obj, number=i)
                for i in range(1, n + 1)
                if i not in existing
            ]
            if new_seats:
                Seat.objects.bulk_create(new_seats, ignore_conflicts=True)


admin.site.register(Seat)
admin.site.register(Departure)
