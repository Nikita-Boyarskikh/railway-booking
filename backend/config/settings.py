import os
from pathlib import Path

import django_stubs_ext
from corsheaders.defaults import default_headers
from django.utils.translation import gettext_lazy as _
from dotenv import load_dotenv

load_dotenv()
django_stubs_ext.monkeypatch()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

INTERNAL_IPS = ["127.0.0.1"]
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")
CORS_ALLOWED_ORIGINS = os.environ.get(
    "DJANGO_CORS_ALLOWED_ORIGINS",
    "http://localhost:8080",
).split(",")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CORS_ALLOW_HEADERS = [*default_headers, "x-request-id"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "corsheaders",
    "rest_framework",
    "constance",
    "djmoney",
    "health_check",
    "apps.core",
    "apps.stations",
    "apps.routes",
    "apps.trains",
    "apps.bookings",
]

if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]

MIDDLEWARE = [
    "apps.core.middleware.RequestIDMiddleware",
    "apps.core.middleware.RequestLoggingMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "railway"),
        "USER": os.environ.get("POSTGRES_USER", "railway"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "railway"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "OPTIONS": {
            "pool": {
                "max_lifetime": int(os.environ.get("DB_POOL_MAX_LIFETIME", "600")),
                "min_size": int(os.environ.get("DB_POOL_MIN_SIZE", "2")),
                "max_size": int(os.environ.get("DB_POOL_MAX_SIZE", "10")),
            },
        },
    }
}

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/0"),
        "TIMEOUT": int(os.environ.get("REDIS_TIMEOUT", "60")),
    },
}

# ---------------------------------------------------------------------------
# Application-level cache TTLs (seconds)
# ---------------------------------------------------------------------------
CACHE_TTL_STATIONS = (
    int(os.environ.get("CACHE_TTL_STATIONS", "0")) or 24 * 60 * 60
)  # 1 day — invalidated by signals
CACHE_TTL_SEARCH = (
    int(os.environ.get("CACHE_TTL_SEARCH", "0")) or 30
)  # departure search — coarse staleness acceptable
CACHE_TTL_SEATS = (
    int(os.environ.get("CACHE_TTL_SEATS", "0")) or 30
)  # seat listing — generation-keyed, stale entries orphan
CACHE_TTL_STATION_ORDER_MAPS = (
    int(os.environ.get("CACHE_TTL_STATION_ORDER_MAPS", "0")) or 60
)  # route station-order maps — signal-invalidated
GENERATION_CACHE_TTL = (
    int(os.environ.get("GENERATION_CACHE_TTL", "0")) or 7 * 24 * 60 * 60
)  # 7 days

API_VERSION = 1

CURRENCIES = ("USD",)
DEFAULT_CURRENCY = "USD"
SERIALIZATION_MODULES = {"json": "djmoney.serializers"}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": int(os.environ.get("PAGE_SIZE", "20")),
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.AnonRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"anon": f"{os.environ.get('THROTTLE_RATE_RPS', '10')}/s"},
}

FIXTURE_DIRS = [BASE_DIR / "fixtures"]

CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"
CONSTANCE_DATABASE_CACHE_BACKEND: str | None = "default"
CONSTANCE_ADDITIONAL_FIELDS = {
    "decimal_field": [
        "django.forms.fields.DecimalField",
        {"max_digits": 10, "decimal_places": 2},
    ],
}
CONSTANCE_CONFIG = {
    "BASE_PRICE": (
        os.environ.get("DEFAULT_BASE_PRICE", "0"),
        _("Fixed amount added to every booking, not multiplied by price factors"),
        "decimal_field",
    ),
}

# ---------------------------------------------------------------------------
# Logging — structured output to stdout for Docker / gunicorn
# ---------------------------------------------------------------------------
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "apps.core.middleware.RequestIDFilter",
        },
    },
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s [%(request_id)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "filters": ["request_id"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "level": "INFO",
            "propagate": True,
        },
        "django.db.backends": {
            "level": "WARNING",
            "propagate": False,
            "handlers": ["console"],
        },
        "apps": {
            "level": LOG_LEVEL,
            "propagate": True,
        },
        "apps.request": {
            "level": LOG_LEVEL,
            "propagate": False,
            "handlers": ["console"],
        },
    },
}
