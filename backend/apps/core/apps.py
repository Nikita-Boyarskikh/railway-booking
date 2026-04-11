from django.apps import AppConfig


class CoreConfig(AppConfig):
    """App config for shared utilities (pricing, availability, timetable)."""

    name = "apps.core"

    def ready(self) -> None:
        """Wire up cache-invalidation signals on startup."""
        from apps.core import signals  # noqa: F401
