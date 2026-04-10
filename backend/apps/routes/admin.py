from django.contrib import admin

from .models import Route, RouteSegment


class RouteSegmentInline(admin.TabularInline[RouteSegment, Route]):
    model = RouteSegment
    extra = 0


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin[Route]):
    inlines = [RouteSegmentInline]


admin.site.register(RouteSegment)
