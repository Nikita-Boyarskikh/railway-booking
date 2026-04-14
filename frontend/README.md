# Railway Booking — Frontend

React 19 + TypeScript SPA for the railway booking prototype.

## Stack

- TypeScript + React 19 (Actions, `useActionState`, `<title>` as JSX metadata)
- Vite 8 (Rolldown + Oxc) — dev server + build
- Tailwind CSS 4
- React Router 7 in **data mode** (`createBrowserRouter`, `loader`/`action`, lazy routes)
- [ky](https://github.com/sindresorhus/ky) HTTP client + [zod](https://zod.dev) runtime schemas
- [react-hook-form](https://react-hook-form.com) + `@hookform/resolvers/zod` for forms
- [@headlessui/react](https://headlessui.com) combobox for the station autocomplete
- [react-i18next](https://react.i18next.com) (en/ru) with browser language detection
- [js-cookie](https://github.com/js-cookie/js-cookie) for CSRF cookie read
- [use-debounce](https://www.npmjs.com/package/use-debounce) for input debouncing
- [@sentry/react](https://docs.sentry.io/platforms/javascript/guides/react/) — opt-in via `VITE_SENTRY_DSN`
- [Bun](https://bun.sh) — package manager & runtime
- ESLint (flat config, `strictTypeChecked` + `stylisticTypeChecked`) + Vitest + Testing Library
- Husky pre-commit hooks

## Structure

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts         # ApiClient (ky + CSRF + timeout + schema-validated methods)
│   │   ├── schemas.ts        # zod schemas (source of truth for API types)
│   │   ├── errors.ts         # ApiError / TimeoutError / SchemaError
│   │   └── cache.ts          # Stations list in-memory cache
│   ├── components/           # View components (props-only, minimal hooks)
│   ├── hooks/                # Logic hooks (useSearch, useSeatsForm, useSeatPricing, useOrderSubmit, useSeatsPage, useToggleSet)
│   ├── pages/                # Route entries; each file exports default page + its loader
│   ├── i18n/                 # i18next init + locales/{en,ru}.json + type augmentation
│   ├── utils/                # format, seat, validation (pure helpers)
│   ├── tests/                # Vitest setup + tests
│   ├── config.ts             # Env-driven constants (API base URL, timeouts, Sentry, locales)
│   ├── sentry.ts             # Sentry.init wrapper (no-op if DSN is empty)
│   ├── routes.tsx            # createBrowserRouter with lazy routes + RouteErrorBoundary
│   ├── main.tsx              # Entry: RouterProvider wrapped in Sentry.ErrorBoundary
│   └── index.css             # Tailwind entry
├── .husky/                   # git hooks
├── eslint.config.js          # Strict type-checked flat config
├── vite.config.ts            # Vite + Vitest config
├── tsconfig.json             # Strict TS (exactOptionalPropertyTypes, noUncheckedIndexedAccess, ...)
├── nginx.conf                # Nginx config
└── Dockerfile
```

State is **URL params + loader data + React Hook Form**; no global store. Stations list is deduped via a module-level cache with TTL.

## Pages

| Route | File | Params | Description |
|---|---|---|---|
| `/` | `pages/Search.page.tsx` | query: `from`, `to`, `date` | Pick station from/to + date, search departures (URL-driven, shareable, back/forward-safe) |
| `/departures/:id/seats` | `pages/Seats.page.tsx` | path: `id` (departure uuid); query: `from`, `to` (station codes) | Pick seats for the chosen segment, fill passenger data (RHF + zod), book |
| `/orders/:id` | `pages/Confirmation.page.tsx` | path: `id` (order uuid) | Confirmation screen with booking details |
| `*` | `pages/NotFound.page.tsx` | — | 404 fallback (also shown when a loader throws `Response { status: 404 }`) |

Loader errors route into `routes.tsx:RouteErrorBoundary`, which renders `NotFound.page.tsx` for 404 and `Error.page.tsx` otherwise.

## Environment variables

All public vars are prefixed `VITE_` and inlined at build time. See `../.env.example` for defaults.

| Var | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `/api/v1` | Backend base URL prefix |
| `VITE_DEFAULT_API_TIMEOUT_MS` | `10000` | Request timeout in ms |
| `VITE_STATIONS_CACHE_MS` | `300000` | Stations list in-memory TTL |
| `VITE_DEFAULT_LOCALE` | `en` | i18n fallback language (supported: `en`, `ru`) |
| `VITE_SENTRY_DSN` | _empty_ | Enable Sentry when set |
| `VITE_SENTRY_ENVIRONMENT` | Vite `MODE` | Sentry environment tag |
| `VITE_SENTRY_SAMPLE_TRACE` | `0.1` | Sentry performance sample rate |

## Setup (local)

```bash
cd frontend
nvm use
bun install
```

## Common commands

| Task | Command |
|---|---|
| Dev server | `bun run dev` |
| Production build | `bun run build` |
| Preview built bundle | `bun run start` |
| Lint | `bun run lint` |
| Type check | `bunx tsc --noEmit` |
| Run tests | `bun run test` |
| Watch tests | `bun run test:watch` |

## Docker

The whole stack is wired in `../docker-compose.yml`:

```bash
docker compose up --build
```
