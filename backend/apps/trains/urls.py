from django.urls import path

from .views import DepartureSearchView, DepartureSeatsView

urlpatterns = [
    path("departures/", DepartureSearchView.as_view(), name="departure-search"),
    path("departures/<int:pk>/seats/", DepartureSeatsView.as_view(), name="departure-seats"),
]
