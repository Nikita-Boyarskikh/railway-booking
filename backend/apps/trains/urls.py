from django.urls import path

from apps.trains.views import DepartureDetailView, DepartureSearchView, DepartureSeatsView

urlpatterns = [
    path("", DepartureSearchView.as_view(), name="departure-search"),
    path("<uuid:uuid>/", DepartureDetailView.as_view(), name="departure"),
    path("<uuid:uuid>/seats/", DepartureSeatsView.as_view(), name="departure-seats"),
]
