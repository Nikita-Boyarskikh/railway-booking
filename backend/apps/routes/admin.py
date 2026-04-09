from django.contrib import admin

from .models import Route, RouteSegment


class RouteSegmentInline(admin.TabularInline):
    model = RouteSegment
    extra = 0


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    inlines = [RouteSegmentInline]


admin.site.register(RouteSegment)
