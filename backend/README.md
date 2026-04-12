# Railway Booking — Backend

Django 6 + DRF API for the railway booking prototype.

## Stack

- Python 3.14
- Django 6.0 + Django REST Framework
- PostgreSQL 18
- Gunicorn (prod), Django dev server (local)
- [uv](https://docs.astral.sh/uv/) for dependency management
- [django-constance](https://django-constance.readthedocs.io/) for runtime, admin-editable configuration (e.g. `BASE_PRICE`)
- Redis (via Django's built-in `RedisCache` backend) for response caching
- ruff (lint + format), mypy + django-stubs (strict type checking), pytest + pytest-django

## Structure

```
backend/
├── config/              # Django project: settings, urls, wsgi
├── apps/
│   ├── core/            # Pricing, availability, timetable utils (no models — runtime config in django-constance)
│   ├── stations/        # Station, Connection models + API
│   ├── routes/          # Route, RouteSegment models
│   ├── trains/          # Train, Car, Seat, Departure models + API
│   └── bookings/        # Order, Booking, Passenger models + API
├── fixtures/demo.json   # Seed data loaded on container start
├── tests/               # pytest suite
├── entrypoint.sh        # migrate + loaddata + collectstatic + gunicorn
├── pyproject.toml       # deps + ruff + pytest config
└── Dockerfile
```

Business logic lives in `services.py` modules per app. Performance-sensitive
helpers (`apps/core/availability.py`, `apps/core/pricing.py`) read from
prefetched `Route.route_segments` where available and fall back to a single
`select_related` query otherwise, so departure-search query count stays
constant regardless of booking volume — see `tests/test_queries.py` for the
regression ceiling.

The `Car` admin (`apps/trains/admin.py`) exposes a `seats_to_create` bulk
helper: set it on the car change form to create seats numbered `1..N`
(skipping existing numbers) in a single `bulk_create` call. Seats can also
be edited inline on the car page, and cars are still editable inline on
the train page.

### Caching layer

Response caching lives in `apps/core/cache.py` and uses Django's cache
framework (Redis in compose via `REDIS_URL`, `LocMemCache` in tests):

| Key | What | TTL | Invalidation |
|---|---|---|---|
| `stations:all` | `GET /api/v1/stations/` response | 1 day | `post_save`/`post_delete` signal on `Station` |
| `search:{from}:{to}:{date}` | `search_departures` output | 30 s | TTL-only; a short window of stale free counts is acceptable |
| `seats:{uuid}:{from}:{to}:g{gen}` | `list_seats` output | 60 s | Generation counter `dep:gen:{uuid}` bumped by `create_order` via `transaction.on_commit` — stale keys orphan and die on TTL |

Signals are wired in `apps/core/apps.py:CoreConfig.ready()`.

## Setup (local)

```bash
cd backend
uv sync                       # install deps (incl. dev group)
cp ../.env.example ../.env    # configure DB credentials
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py collectstatic
uv run python manage.py loaddata fixtures/demo.json
uv run python manage.py runserver
```

API: http://localhost:8000/api/v1/ — admin: http://localhost:8000/admin/

## Common commands

| Task                 | Command                                               |
|----------------------|-------------------------------------------------------|
| Run dev server       | `uv run python manage.py runserver`                   |
| Make migrations      | `uv run python manage.py makemigrations`              |
| Apply migrations     | `uv run python manage.py migrate`                     |
| Load demo fixtures   | `uv run python manage.py loaddata fixtures/demo.json` |
| Create superuser     | `uv run python manage.py createsuperuser`             |
| Collect admin static | `uv run python manage.py collectstatic`               |
| Django shell         | `uv run python manage.py shell`                       |
| Run tests            | `uv run pytest`                                       |
| Run tests (verbose)  | `uv run pytest -v`                                    |
| Single test          | `uv run pytest tests/test_api.py::test_name`          |
| Lint                 | `uv run ruff check .`                                 |
| Lint + autofix       | `uv run ruff check --fix .`                           |
| Format               | `uv run ruff format .`                                |
| Type check           | `uv run mypy .`                                       |

## Docker

The whole stack is wired in `../docker-compose.yml`:

```bash
docker compose up --build
```

The backend container runs gunicorn on `:8000`.
Nginx in the frontend container proxies `/api/` to it and exposes admin at `/admin/`.

## API endpoints

The API uses public identifiers only: stations by `code`, departures and orders by `uuid`, seats by `(car_number, seat_number)`. Internal integer PKs are never serialized.

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/stations/` | List stations as `[{name, code}]` |
| GET | `/api/v1/departures/?from={code}&to={code}&date={YYYY-MM-DD}` | Search departures (returns `uuid`, train info, times, free count, min price) |
| GET | `/api/v1/departures/{uuid}/seats/?from={code}&to={code}` | Seats grouped by car (`number`, `car_type`, `seats[]` with `number`, `seat_type`, `status`, `price`) |
| POST | `/api/v1/orders/` | Create order (see payload below) |
| GET | `/api/v1/orders/{uuid}/` | Retrieve an order by uuid |

### Create-order payload

```json
{
  "departure_uuid": "9d6e6f8a-…",
  "station_from_code": "MOW",
  "station_to_code": "SOC",
  "items": [
    {
      "car_number": 2,
      "seat_number": 17,
      "passenger": {
        "name": "John Doe",
        "passport_number": "1234567890",
        "gender": "male",
        "birth_date": "1990-01-15"
      }
    }
  ]
}
```

Response: `{uuid, created_at, total_price, features, bookings[]}`. Each booking carries `departure_uuid`, `car_number`, `seat_number`, `station_from_code`, `station_to_code`, and an embedded `passenger`. On a 409 conflict the body is `{detail, car_number, seat_number}`.
