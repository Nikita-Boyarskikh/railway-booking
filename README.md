# Railway Booking System

Prototype web app for selling long-distance railway tickets with per-segment seat availability.
See [AGENTS.md](AGENTS.md) for the full specification, [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md) for per-service docs.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:8080
- API: http://localhost:8080/api/

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

## Frontend pages

| Route | Params | Description |
|---|---|---|
| `/` | — | Search: pick station from/to + date, list departures |
| `/departures/:id/seats` | path: `id`; query: `from`, `to` (station ids) | Pick seats for the chosen segment, fill passenger data |
| `/orders/:id` | path: `id` | Booking confirmation |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stations/` | List all stations |
| GET | `/api/departures/?from=&to=&date=` | Search departures |
| GET | `/api/departures/{id}/seats/?from=&to=` | Seats grouped by car |
| POST | `/api/orders/` | Create order with bookings |
| GET | `/api/orders/{id}/` | Retrieve an order |

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

- **Backend**: Python 3.14 + Django 6.0 + DRF + PostgreSQL 18
- **Frontend**: React 19 + Vite + Tailwind 4 + React Router
- **Infra**: Docker Compose, Nginx
