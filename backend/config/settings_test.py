from .settings import *  # noqa: F403

DEBUG = True
SECRET_KEY = "dev-insecure-secret-key-change-me"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
