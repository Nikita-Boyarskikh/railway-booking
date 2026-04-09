from django.contrib import admin

from .models import Car, Departure, Seat, Train


class CarInline(admin.TabularInline):
    model = Car
    extra = 0


@admin.register(Train)
class TrainAdmin(admin.ModelAdmin):
    inlines = [CarInline]
    list_display = ("number", "name", "route")


admin.site.register(Car)
admin.site.register(Seat)
admin.site.register(Departure)
