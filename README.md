# Railway Booking System

Prototype web app for selling long-distance railway tickets with per-segment seat availability.
See [AGENTS.md](AGENTS.md) for the full specification, [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md) for per-service docs.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:8080
- API: http://localhost:8080/api/v1/

The backend container automatically runs migrations and loads demo fixtures
(stations, segments, routes, trains, cars, seats, and departures).

## Development (hot reload)

For hot reloading on both services, layer the dev override on top of the base file:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --watch
```

- **Backend** — source mounted into the container, gunicorn runs with `--reload`, so Python changes restart workers automatically.
- **Frontend** — Vite dev server replaces the nginx prod build; source is mounted, HMR is enabled, served at http://localhost:8080.

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

The frontend build needs no env vars; the dev override sets `VITE_API_PROXY=http://backend:8000` for the Vite dev server.

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
docker compose exec backend uv run pytest
docker compose exec frontend bun test
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
