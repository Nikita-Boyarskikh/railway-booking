import os
import socket
from pathlib import Path

import django_stubs_ext
from corsheaders.defaults import default_headers
from django.utils.translation import gettext_lazy
from dotenv import load_dotenv

load_dotenv()
django_stubs_ext.monkeypatch()

# ---------------------------------------------------------------------------
# Sentry — error monitoring & performance tracing
# ---------------------------------------------------------------------------
if SENTRY_DSN := os.environ.get("SENTRY_DSN", ""):
    import sentry_sdk

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
        traces_sample_rate=float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        profiles_sample_rate=float(os.environ.get("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
        send_default_pii=False,
    )

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS = [ip[:-1] + "1" for ip in ips] + ["127.0.0.1"]
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")

if DEBUG:
    ALLOWED_HOSTS = ["*"]
    CORS_ALLOW_ALL_ORIGINS = True

allowed_origins = ",".join(f"http://{host}" for host in ALLOWED_HOSTS)
CSRF_TRUSTED_ORIGINS = os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", allowed_origins).split(",")
CORS_ALLOWED_ORIGINS = os.environ.get("DJANGO_CORS_ALLOWED_ORIGINS", allowed_origins).split(",")

USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CORS_ALLOW_HEADERS = [*default_headers, "x-request-id"]
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG

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
    *(["debug_toolbar"] if DEBUG else []),
    "django_prometheus",
    "apps.core",
    "apps.stations",
    "apps.routes",
    "apps.trains",
    "apps.bookings",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "apps.core.middleware.RequestIDMiddleware",
    "apps.core.middleware.RequestLoggingMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *(["debug_toolbar.middleware.DebugToolbarMiddleware"] if DEBUG else []),
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

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
CONN_MAX_AGE = int(os.environ.get("CONN_MAX_AGE", "600"))

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/0").split(","),
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
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": f"{os.environ.get('THROTTLE_RATE_RPS', '10')}/s",
        "booking": f"{os.environ.get('BOOKING_THROTTLE_RATE_RPS', '1')}/s",
    },
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
        gettext_lazy("Fixed amount added to every booking, not multiplied by price factors"),
        "decimal_field",
    ),
}

# ---------------------------------------------------------------------------
# Logging — JSON to stdout for Docker / gunicorn / ELK / CloudWatch
# ---------------------------------------------------------------------------
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
LOG_FORMAT = os.environ.get("LOG_FORMAT", "text" if DEBUG else "json")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "request_id": {
            "()": "apps.core.middleware.RequestIDFilter",
        },
    },
    "formatters": {
        "text": {
            "format": "%(asctime)s [%(levelname)s] %(name)s [%(request_id)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "json": {
            "class": "pythonjsonlogger.json.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
            "rename_fields": {"asctime": "timestamp", "levelname": "level", "name": "logger"},
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": LOG_FORMAT,
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

SILENCED_SYSTEM_CHECKS = [
    "security.W004",
    "security.W008",
    "security.W009",
]

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: True,
}
