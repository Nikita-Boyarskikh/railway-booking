from django.urls import path

from apps.trains.views import DepartureSearchView, DepartureSeatsView

urlpatterns = [
    path("departures/", DepartureSearchView.as_view(), name="departure-search"),
    path("departures/<uuid:uuid>/seats/", DepartureSeatsView.as_view(), name="departure-seats"),
]
