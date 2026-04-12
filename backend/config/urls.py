"""Root URL configuration for the Railway Booking project."""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", HealthCheckView.as_view(), name="health_check"),
    path(f"api/v{settings.API_VERSION}/", include([
        path('stations/', include("apps.stations.urls")),
        path('departures/', include("apps.trains.urls")),
        path('orders/', include("apps.bookings.urls")),
    ])),
]
