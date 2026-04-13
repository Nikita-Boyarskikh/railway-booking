from itertools import pairwise
from typing import TYPE_CHECKING

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, ModelForm
from django.utils.translation import gettext_lazy as _

from apps.bookings.models import Booking
from apps.routes.models import Route, RouteSegment

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from django.http import HttpRequest


class RouteSegmentFormSet(BaseInlineFormSet[RouteSegment, Route, ModelForm[RouteSegment]]):
    def clean(self) -> None:
        """Validates that segments form a continuous chain: A→B, B→C, C→D, …"""
        super().clean()

        # Collect non-deleted forms with data.
        segments: list[tuple[int, int, int]] = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get("DELETE"):
                connection = form.cleaned_data.get("connection")
                order = form.cleaned_data.get("order")
                if connection is not None and order is not None:
                    segments.append((order, connection.station_from_id, connection.station_to_id))

        if not segments:
            raise ValidationError(_("Route should not be empty."))

        segments.sort()

        # Check order values are sequential 0..N-1 (no gaps/duplicates).
        expected_orders = list(range(len(segments)))
        actual_orders = [s[0] for s in segments]
        if actual_orders != expected_orders:
            raise ValidationError(
                _(
                    "Segment orders must be sequential starting from 0 "
                    f"(expected {expected_orders}, got {actual_orders})."
                )
            )

        # Check chain continuity: each segment's station_from must match
        # the previous segment's station_to.
        for prev_segment, next_segment in pairwise(segments):
            if prev_segment[2] != next_segment[1]:
                raise ValidationError(
                    _(
                        f"Segment #{next_segment[0]} start station does not match "
                        f"segment #{prev_segment[0]} end station — route is not continuous."
                    )
                )


def _route_has_bookings(route: Route) -> bool:
    """Check if any departure on this route has bookings."""
    return Booking.objects.filter(departure__train__route=route).exists()


class RouteSegmentInline(admin.TabularInline[RouteSegment, Route]):
    model = RouteSegment
    formset = RouteSegmentFormSet
    extra = 0

    def _is_readonly(self, obj: Route | None) -> bool:
        return obj is not None and obj.pk is not None and _route_has_bookings(obj)

    def has_add_permission(self, request: HttpRequest, obj: Route | None = None) -> bool:
        if self._is_readonly(obj):
            return False
        return super().has_add_permission(request, obj)

    def has_change_permission(self, request: HttpRequest, obj: Route | None = None) -> bool:  # type: ignore[override]
        if self._is_readonly(obj):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj: Route | None = None) -> bool:  # type: ignore[override]
        if self._is_readonly(obj):
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin[Route]):
    inlines = (RouteSegmentInline,)
    list_display = ("name", "price_factor")
    search_fields = ("name",)


@admin.register(RouteSegment)
class RouteSegmentAdmin(admin.ModelAdmin[RouteSegment]):
    """Read-only view — segments should be edited via the RouteAdmin inline."""

    list_display = (
        "route__name",
        "order",
        "connection",
        "connection__base_price",
        "connection__distance_km",
        "stop_duration",
    )
    search_fields = (
        "route__name",
        "connection__station_from__code",
        "connection__station_from__name",
        "connection__station_to__code",
        "connection__station_to__name",
    )
    ordering = (
        "route",
        "order",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: RouteSegment | None = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: RouteSegment | None = None) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> QuerySet[RouteSegment]:
        return (
            super()
            .get_queryset(request)
            .select_related("route", "connection__station_from", "connection__station_to")
        )
