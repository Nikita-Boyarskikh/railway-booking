from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.stations.urls")),
    path("api/", include("apps.trains.urls")),
    path("api/", include("apps.bookings.urls")),
]
