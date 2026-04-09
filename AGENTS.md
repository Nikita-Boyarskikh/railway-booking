# Railway Booking System — Project Context

## Overview

A prototype web application for selling long-distance railway tickets. Passengers can board and exit at any intermediate station along a train's route. The system tracks seat availability per segment (span between adjacent stations), allowing the same seat to be sold to different passengers on non-overlapping segments.

## Business Requirements

### In Scope

- Search for departures from station A to station B on a given date
- View available seats and prices for a specific departure
- Book one or more seats in a single order (one departure per order)
- Passenger data entered per seat (name, passport number, gender, birth date)
- Admin panel for managing stations, segments, routes, trains, cars, seats, departures, config

### Out of Scope (for prototype)

- User registration / authentication
- Payment processing
- Ticket returns / cancellations
- Notifications
- Multi-language support
- Visual wagon/seat map (table view instead)

### Extensibility Considerations

The data model is designed so the following can be added later without major schema changes:

- Car types (SV, platzkart, compartment) — `car_type` str field exists
- Seat types (upper, lower, side) — `seat_type` str field exists
- Car features (bio-toilet, AC, pets allowed) — `features` JSONField exists
- Schedule variations (per-date, periodic) — `Departure` model is separate from `Train`
- Stop durations — `stop_duration` field in `RouteSegment`
- Additional services
- Multiple bookings for different passengers
- Document-based passenger identification — `Passenger` model has passport, gender, birth_date fields
- Train features (wagon restaurant, baggage wagon) — `features` JSONField exists
- Order features (refundable, insurance) — `features` JSONField exists
- Route features (cross-border) — `features` JSONField exists

## Data Model

### Station

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| name | str | |
| code | str | unique short code, unique index |

### Segment

A span of track between two adjacent stations.

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| station_from | FK → Station | |
| station_to | FK → Station | |
| distance_km | decimal | |
| base_price | decimal | price for this segment |

### Route

An ordered sequence of segments forming a complete path.

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| name | str | e.g. "Moscow — Sochi" |
| price_factor | decimal | default 1.0 |
| features | JSON | {} for now, extensible (e.g. cross-border) |

### RouteSegment

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| route | FK → Route | unique together with segment; unique together with order |
| segment | FK → Segment | |
| order | int | sequence number in route |
| stop_duration | duration | default 0, stop time at segment's station_from |

### Train

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| route | FK → Route | |
| number | str | unique index |
| name | str | optional display name |
| avg_speed_kmh | decimal | for travel time calculation |
| price_factor | decimal | default 1.0 |
| features | JSON | {} for now, extensible (e.g. restaurant wagon, baggage wagon) |

### Car

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| train | FK → Train | unique together with number |
| number | int | car number in train |
| car_type | str | "common" for now, extensible (sv, platzkart, compartment) |
| features | JSON | {} for now, extensible (bio-toilet, AC, pets) |
| price_factor | decimal | default 1.0 |

### Seat

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| car | FK → Car | unique together with number |
| number | int | seat number within car |
| seat_type | str | "common" for now, extensible (upper, lower, side) |
| price_factor | decimal | default 1.0 |

### Departure

A specific run of a train on a given date.

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| train | FK → Train | |
| date | date | |
| departure_time | time | from the first station |

Time at any intermediate station is computed:
`departure_time + sum(distance_km / train.avg_speed_kmh) + sum(stop_durations)` for all preceding segments.

### Passenger

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| name | str | full name |
| passport_number | str | |
| gender | str | "male" / "female" |
| birth_date | date | |

### Order

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| created_at | datetime | |
| total_price | decimal | |
| features | JSON | {} for now, extensible (e.g. refundable, insurance) |

### Booking

| Field | Type | Notes |
|-------|------|-------|
| id | PK | |
| order | FK → Order | |
| departure | FK → Departure | |
| seat | FK → Seat | |
| station_from | FK → Station | boarding station |
| station_to | FK → Station | alighting station |
| passenger | FK → Passenger | |

### Config (singleton)

| Field | Type | Notes |
|-------|------|-------|
| base_price | decimal | fixed addition per booking |

## Pricing Formula

```
booking_price = base_price + sum(segment.base_price for each segment in route from A to B) * route.price_factor * train.price_factor * car.price_factor * seat.price_factor

order.total_price = sum(booking_price for each booking in order)
```

`base_price` is a fixed amount from Config, NOT multiplied by price factors.

## Seat Availability Logic

A seat is occupied on a segment if any existing Booking for that seat/departure overlaps with that segment. Overlap is determined by comparing segment order ranges within the route.

For prototype: availability is computed dynamically from the Booking table (no denormalized occupancy table). Query approach:

1. For a given departure + station_from + station_to, determine the range of RouteSegment orders.
2. Find all Bookings for the same departure + seat where the booked segment range overlaps.
3. A seat is free if no overlapping bookings exist.

Concurrency: use `select_for_update` within `transaction.atomic` when creating bookings to prevent double-booking.

## User Scenarios

### 1. Search Departures

- User selects: station from (autocomplete on frontend, full list from API), station to, date
- `GET /api/stations/` — returns all stations
- `GET /api/departures/?from={id}&to={id}&date={YYYY-MM-DD}`
- Response per departure: train number/name, departure time at station A, arrival time at station B, travel duration, free seat count, minimum price

### 2. View Seats

- User clicks "Select" on a departure
- `GET /api/departures/{id}/seats/?from={station_id}&to={station_id}`
- Response: seats grouped by car, each seat with: number, type, status (free/occupied), price
- User selects one or more seats

### 3. Book

- User enters passenger data per selected seat (name, passport, gender, birth date), sees total price
- `POST /api/orders/`
- Request body:
  ```json
  {
    "departure_id": 1,
    "station_from_id": 1,
    "station_to_id": 5,
    "items": [
      {"seat_id": 42, "passenger_name": "John Doe", "passenger_passport": "1234567890", "passenger_gender": "male", "passenger_birth_date": "1990-01-15"}
    ]
  }
  ```
- System validates seat availability within a transaction
- Response: order ID, booking details, total price
- On conflict: error response, user sees "seat no longer available"

## Tech Stack

- **Backend**: Python 3.14, Django 6.0, Django REST Framework, Gunicorn, uv (dependency management)
- **Frontend**: TypeScript, React 19, Vite, Tailwind CSS 4, React Router, Bun (package manager & runtime)
- **Database**: PostgreSQL 18
- **Infrastructure**: Docker Compose, Nginx
- **Code quality**: ruff (PEP8), pytest, ESLint (Airbnb style)
- **Language**: English (code, docs, API)

## Project Structure

```
railway-booking/
├── docker-compose.yml
├── README.md
├── AGENTS.md
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml          # uv managed dependencies
│   ├── manage.py
│   ├── config/              # settings, urls, wsgi
│   ├── apps/
│   │   ├── stations/        # Station, Segment models + API
│   │   ├── routes/          # Route, RouteSegment models + API
│   │   ├── trains/          # Train, Car, Seat, Departure models + API
│   │   ├── bookings/        # Order, Booking, Passenger models + API
│   │   └── core/            # Config model, shared utils (timetable calc, pricing)
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── src/
│   │   ├── api/             # API client functions
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/           # SearchPage, SeatsPage, ConfirmationPage
│   │   └── types/           # TypeScript interfaces
│   └── ...
└── .env
```

## Architecture Decisions

- **Service layer**: business logic (pricing, availability checks) lives in `services.py` within each app, not in views or serializers
- **Timetable computation**: utility in `core` app that takes a Departure and returns `[{station, arrival_time, departure_time}, ...]`
- **No state management library**: React local state + URL params, data fetched per page
- **Nginx**: single container (frontend) serves built React static files and proxies `/api/` to the backend (gunicorn)
- **Migrations + seed data**: `migrate` + `loaddata` run on backend container startup with demo fixtures (stations, segments, routes, trains, cars, seats, and departures)
- **Environment variables**: `.env` file for DB credentials, SECRET_KEY, etc.

## API Endpoints Summary

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stations/` | List all stations |
| GET | `/api/departures/?from=&to=&date=` | Search departures |
| GET | `/api/departures/{id}/seats/?from=&to=` | Seats grouped by car |
| POST | `/api/orders/` | Create order with bookings |
