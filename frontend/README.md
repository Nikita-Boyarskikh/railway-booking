# Railway Booking — Frontend

React 19 + TypeScript SPA for the railway booking prototype.

## Stack

- TypeScript + React 19
- Vite (dev server + build)
- Tailwind CSS 4
- React Router 7
- [Bun](https://bun.sh) — package manager & runtime
- ESLint (flat config) + Vitest + Testing Library
- Husky pre-commit hooks

## Structure

```
frontend/
├── src/
│   ├── api/              # API client (fetch wrappers)
│   ├── components/       # Reusable UI (StationAutocomplete, ...)
│   ├── pages/            # Pages (SearchPage, SeatsPage, ConfirmationPage, ...)
│   ├── types/            # Shared TS interfaces
│   ├── tests/            # Vitest setup + tests
│   ├── App.tsx           # Router
│   ├── main.tsx          # Entry
│   └── index.css         # Tailwind entry
├── .husky/               # git hooks
├── eslint.config.js      # ESLint config
├── vite.config.ts        # Vite + Vitest config
├── tsconfig.json         # TypeScript config
├── nginx.conf            # Nginx config
└── Dockerfile
```

State is local + URL params; data is fetched per page. No global store.

## Pages

| Route | Component | Params | Description |
|---|---|---|---|
| `/` | `SearchPage` | — | Pick station from/to + date, search departures |
| `/departures/:id/seats` | `SeatsPage` | path: `id` (departure **uuid**); query: `from`, `to` (station **codes**) | Pick seats for the chosen segment, fill passenger data |
| `/orders/:id` | `ConfirmationPage` | path: `id` (order **uuid**); router state: created `order` | Confirmation screen with booking details |

## Setup (local)

```bash
cd frontend
bun install
bun run dev
```

## Common commands

| Task | Command |
|---|---|
| Dev server | `bun run dev` |
| Production build | `bun run build` |
| Preview built bundle | `bun run start` |
| Lint | `bun run lint` |
| Run tests | `bun run test` |
| Watch tests | `bun run test:watch` |

## Docker

The whole stack is wired in `../docker-compose.yml`:

```bash
docker compose up --build
```
