from django.urls import path

from apps.stations.views import StationListView

urlpatterns = [
    path("", StationListView.as_view(), name="station-list"),
]
