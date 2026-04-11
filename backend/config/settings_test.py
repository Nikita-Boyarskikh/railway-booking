from config.settings import *  # noqa: F403

DEBUG = True
SECRET_KEY = "dev-insecure-secret-key-change-me"
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
