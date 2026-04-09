# Railway Booking — Backend

Django 6 + DRF API for the railway booking prototype.

## Stack

- Python 3.14
- Django 6.0 + Django REST Framework
- PostgreSQL 18
- Gunicorn (prod), Django dev server (local)
- [uv](https://docs.astral.sh/uv/) for dependency management
- ruff (lint + format), pytest + pytest-django

## Structure

```
backend/
├── config/              # Django project: settings, urls, wsgi
├── apps/
│   ├── core/            # Config singleton, pricing, availability, timetable utils
│   ├── stations/        # Station, Segment models + API
│   ├── routes/          # Route, RouteSegment models
│   ├── trains/          # Train, Car, Seat, Departure models + API
│   └── bookings/        # Order, Booking, Passenger models + API
├── fixtures/demo.json   # Seed data loaded on container start
├── tests/               # pytest suite
├── entrypoint.sh        # migrate + loaddata + gunicorn
├── pyproject.toml       # deps + ruff + pytest config
└── Dockerfile
```

Business logic lives in `services.py` modules per app.

## Setup (local)

```bash
cd backend
uv sync                       # install deps (incl. dev group)
cp ../.env.example ../.env    # configure DB credentials
uv run python manage.py migrate
uv run python manage.py loaddata fixtures/demo.json
uv run python manage.py runserver
```

API: http://localhost:8000/api/ — admin: http://localhost:8000/admin/

## Common commands

| Task | Command |
|---|---|
| Run dev server | `uv run python manage.py runserver` |
| Make migrations | `uv run python manage.py makemigrations` |
| Apply migrations | `uv run python manage.py migrate` |
| Load demo fixtures | `uv run python manage.py loaddata fixtures/demo.json` |
| Create superuser | `uv run python manage.py createsuperuser` |
| Django shell | `uv run python manage.py shell` |
| Run tests | `uv run pytest` |
| Run tests (verbose) | `uv run pytest -v` |
| Single test | `uv run pytest tests/test_api.py::test_name` |
| Lint | `uv run ruff check .` |
| Lint + autofix | `uv run ruff check --fix .` |
| Format | `uv run ruff format .` |

## Docker

The whole stack is wired in `../docker-compose.yml`:

```bash
docker compose up --build
```

The backend container runs `entrypoint.sh`: migrate → loaddata → gunicorn on `:8000`. Nginx in the frontend container proxies `/api/` to it.

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/stations/` | List stations |
| GET | `/api/departures/?from=&to=&date=` | Search departures |
| GET | `/api/departures/{id}/seats/?from=&to=` | Seats grouped by car |
| POST | `/api/orders/` | Create order with bookings |
