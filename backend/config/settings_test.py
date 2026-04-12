from config.settings import *  # noqa: F403

from corsheaders.defaults import default_headers

INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

ALLOWED_HOSTS = ["*"]
INTERNAL_IPS = ["127.0.0.1"]
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-request-id",
]

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
