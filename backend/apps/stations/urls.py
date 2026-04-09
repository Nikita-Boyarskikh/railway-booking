from django.urls import path

from .views import StationListView

urlpatterns = [
    path("stations/", StationListView.as_view(), name="station-list"),
]
