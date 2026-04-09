#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py loaddata demo || true
python manage.py collectstatic --noinput

gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --reload --access-logfile -
