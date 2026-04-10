"""Signal handlers for cache invalidation."""

from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.stations.models import Station

from .cache import invalidate_stations


@receiver([post_save, post_delete], sender=Station)
def _invalidate_stations_cache(sender: type[Station], **kwargs: Any) -> None:
    """Drop the cached station list whenever a Station row changes."""
    invalidate_stations()
