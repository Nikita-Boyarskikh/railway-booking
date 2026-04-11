"""Django admin registrations for the trains app."""

from typing import Any

from django import forms
from django.contrib import admin
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from apps.trains.models import Car, Departure, Seat, Train


class BaseCarAdminForm(forms.ModelForm[Car]):
    """Base form for :class:`Car` with a bulk seat-creation helper."""

    seats_to_create = forms.IntegerField(
        required=False,
        min_value=0,
        help_text=_("Bulk-create N seats numbered 1..N, skipping existing"),
    )

    class Meta:
        model = Car
        fields = ("train", "number", "car_type", "features", "price_factor")


class CarInlineForm(BaseCarAdminForm):
    """Form for :class:`Car` used inside the :class:`CarInline` on the train page."""


class CarInline(admin.TabularInline[Car, Train]):
    """Inline editor for a train's cars on the train change page."""

    model = Car
    form = CarInlineForm
    extra = 0
    show_change_link = True
    fields = ("number", "car_type", "price_factor", "number_of_seats", "seats_to_create")
    readonly_fields = ("number_of_seats",)

    def number_of_seats(self, obj: Car) -> int:
        return obj.seats.count()

    def has_change_permission(self, request: HttpRequest, obj: Train | Car | None = None) -> bool:
        return False


def _bulk_create_seats(car: Car, n: int) -> None:
    """Create seats 1..n on ``car``, skipping numbers that already exist."""
    if n <= 0:
        return
    existing = set(car.seats.values_list("number", flat=True))
    new_seats = [Seat(car=car, number=i) for i in range(1, n + 1) if i not in existing]
    if new_seats:
        Seat.objects.bulk_create(new_seats, ignore_conflicts=True)


@admin.register(Train)
class TrainAdmin(admin.ModelAdmin[Train]):
    """Admin for :class:`Train` with an inline list of cars."""

    inlines = [CarInline]
    list_display = ("number", "name", "route")
    search_fields = ("number", "name", "route__name")
    ordering = ("number",)

    def save_formset(self, request: HttpRequest, form: Any, formset: Any, change: Any) -> None:
        """After saving the car inline formset, bulk-create seats if requested."""
        formset.save()
        for inline_form in formset.forms:
            if not inline_form.cleaned_data or inline_form.cleaned_data.get("DELETE"):
                continue
            n = inline_form.cleaned_data.get("seats_to_create") or 0
            car = inline_form.instance
            if n and car.pk:
                _bulk_create_seats(car, n)
        super().save_formset(request, form, formset, change)


class SeatInline(admin.TabularInline[Seat, Car]):
    """Inline editor for a car's seats on the car change page."""

    model = Seat
    extra = 0
    fields = ("number", "seat_type", "price_factor")


class CarAdminForm(BaseCarAdminForm):
    """Form for :class:`Car` with a bulk seat-creation helper."""


@admin.register(Car)
class CarAdmin(admin.ModelAdmin[Car]):
    """Admin for :class:`Car` with inline seats and optional bulk creation."""

    form = CarAdminForm
    inlines = [SeatInline]
    list_display = ("train", "number", "car_type", "price_factor")
    search_fields = ("train__number", "train__name")
    ordering = ("train", "number")
    list_filter = ("car_type",)

    def save_model(self, request: HttpRequest, obj: Car, form: Any, change: Any) -> None:
        """Save the car and optionally bulk-create seats numbered ``1..N``."""
        super().save_model(request, obj, form, change)
        n = form.cleaned_data.get("seats_to_create") or 0
        _bulk_create_seats(obj, n)


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin[Seat]):
    """Admin for :class:`Seat`."""

    list_display = ("car", "number", "seat_type", "price_factor")
    search_fields = ("car__train__number", "car__train__name")
    ordering = ("car__train__number", "car__number", "number")
    list_filter = ("seat_type",)


@admin.register(Departure)
class DepartureAdmin(admin.ModelAdmin[Departure]):
    """Admin for :class:`Departure`."""

    date_hierarchy = "date"
    list_display = ("train", "date", "departure_time")
    search_fields = ("train__number", "train__name")
    ordering = ("date", "departure_time", "train")
    list_filter = ("date",)
