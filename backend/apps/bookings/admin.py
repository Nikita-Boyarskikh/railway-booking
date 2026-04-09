from django.contrib import admin

from .models import Booking, Order, Passenger

admin.site.register(Passenger)
admin.site.register(Order)
admin.site.register(Booking)
