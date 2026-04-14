# Railway Booking System

Prototype web app for selling long-distance railway tickets with per-segment seat availability.
See [AGENTS.md](AGENTS.md) for the full specification, [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md) for per-service docs.

## Quick start

```bash
cp .env.example .env  # Edit defaults if you need
cd backend; uv run python manage.py collectstatic; cd -
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py loaddata demo
docker compose exec backend python manage.py createsuperuser
```

- Frontend: http://localhost:8080
- API: http://localhost:8080/api/v1/
- Admin: http://localhost:8080/admin/
- Health check: http://localhost:8080/health/
- SwaggerUI API Doc: http://localhost:8080/api/schema/swagger-ui
- Prometeus metrics: http://localhost:8080/metrics/

## Development (hot reload)

For hot reloading on both services, layer the dev override on top of the base file:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --watch
```

- **Backend** — source mounted into the container, gunicorn runs with `--reload`, so Python changes restart workers automatically.
- **Frontend** — Vite dev server replaces the nginx prod build; source is mounted, HMR is enabled, served at http://localhost:8080.

The backend container automatically runs migrations, collects staticfiles and loads demo fixtures
(stations, segments, routes, trains, cars, seats, and departures).

The dev override is opt-in: plain `docker compose up --build` still produces the production-style image (nginx + built bundle).

## Environment variables

Copied from `.env.example` into `.env` and consumed by `docker-compose.yml`.

| Variable | Default            | Used by | Description |
|---|--------------------|---|---|
| `POSTGRES_DB` | `railway`          | db, backend | Postgres database name |
| `POSTGRES_USER` | `railway`          | db, backend | Postgres user |
| `POSTGRES_PASSWORD` | `railway`          | db, backend | Postgres password |
| `POSTGRES_HOST` | `db`               | backend | Postgres host (compose service name) |
| `POSTGRES_PORT` | `5432`             | backend | Postgres port |
| `DJANGO_SECRET_KEY` | `dev-insecure-...` | backend | Django `SECRET_KEY` — replace in any non-dev env |
| `DJANGO_DEBUG` | `0`                | backend | `1` enables Django debug mode |
| `DJANGO_ALLOWED_HOSTS` | `*`                | backend | Comma-separated `ALLOWED_HOSTS` |

The frontend build needs no env vars by default; all `VITE_*` keys below have sane fallbacks. Set them via `frontend/.env` for local dev or via build args/container env in prod. See `frontend/.env.example` for the full list.

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `/api/v1` | Backend prefix; override if the frontend is served from a different origin than the API |
| `VITE_DEFAULT_API_TIMEOUT_MS` | `10000` | Per-request timeout (ms) for the `ky` client |
| `VITE_STATIONS_CACHE_MS` | `300000` | In-memory TTL for the stations list shared across loaders |
| `VITE_DEFAULT_LOCALE` | `en` | UI fallback locale; supported: `en`, `ru` |
| `VITE_SENTRY_DSN` | _empty_ | Enables Sentry error reporting when set |
| `VITE_SENTRY_ENVIRONMENT` | Vite `MODE` | Sentry environment tag (e.g. `production`, `staging`) |
| `VITE_SENTRY_SAMPLE_TRACE` | `0.1` | Sentry performance sample rate (0.0–1.0) |
| `VITE_API_PROXY` | `http://localhost:8000` | Dev-only: backend origin for the Vite dev server proxy (set to `http://backend:8000` in the docker dev override) |

## Frontend pages

| Route | Params | Description |
|---|---|---|
| `/` | — | Search: pick station from/to + date, list departures |
| `/departures/:id/seats` | path: `id` (departure uuid); query: `from`, `to` (station codes) | Pick seats for the chosen segment, fill passenger data |
| `/orders/:id` | path: `id` (order uuid) | Booking confirmation |

## API endpoints

The API exposes public identifiers only — stations by `code`, departures and orders by `uuid`, seats by `(car_number, seat_number)`. Internal integer PKs are never returned.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/stations/` | List all stations as `[{name, code}]` |
| GET | `/api/v1/departures/?from={code}&to={code}&date=` | Search departures |
| GET | `/api/v1/departures/{uuid}/seats/?from={code}&to={code}` | Seats grouped by car |
| POST | `/api/v1/orders/` | Create order with bookings (see backend README for payload) |
| GET | `/api/v1/orders/{uuid}/` | Retrieve an order |

## Tests

```bash
docker compose exec backend pytest
cd frontend
nvm use
bun test
```

## Linters

```bash
docker compose exec backend uv run ruff check .
docker compose exec frontend bun run lint
```

## Stack

- **Backend**: Python 3.14 + Django 6.0 + DRF + PostgreSQL 18 + Redis 8 (cache)
- **Frontend**: React 19 + Vite + Tailwind 4 + React Router
- **Infra**: Docker Compose, Nginx
