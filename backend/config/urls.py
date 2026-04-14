"""Root URL configuration for the Railway Booking project."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from health_check.views import HealthCheckView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("django_prometheus.urls")),
    path(
        "health/",
        HealthCheckView.as_view(
            checks=[
                "health_check.Cache",
                "health_check.Database",
            ]
        ),
        name="health_check",
    ),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        f"api/v{settings.API_VERSION}/",
        include(
            [
                path("stations/", include("apps.stations.urls")),
                path("departures/", include("apps.trains.urls")),
                path("orders/", include("apps.bookings.urls")),
            ]
        ),
    ),
]

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
