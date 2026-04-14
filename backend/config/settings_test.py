from config.settings import *  # noqa: F403
from config.settings import REST_FRAMEWORK

ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True

DEBUG = True
SECRET_KEY = "dev-insecure-secret-key-change-me"  # noqa: S105
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}
CONSTANCE_DATABASE_CACHE_BACKEND = None

REST_FRAMEWORK.update(
    {
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {},
    }
)
