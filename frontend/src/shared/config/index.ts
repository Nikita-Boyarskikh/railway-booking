const env = import.meta.env;

export const DEFAULT_CURRENCY = 'USD';

export const API_VERSION = 1;
export const CSRF_TOKEN_COOKIE = 'csrftoken';
export const UNSAFE_API_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
export const DEFAULT_API_TIMEOUT_MS = Number(env.VITE_DEFAULT_API_TIMEOUT_MS ?? 10_000);
export const DEFAULT_API_PREFIX = env.VITE_API_BASE_URL ?? `/api/v${API_VERSION}`;

export const CACHE_TTL_MS = Number(env.VITE_STATIONS_CACHE_MS ?? 5 * 60 * 1000);

export const DEFAULT_LOCALE = env.VITE_DEFAULT_LOCALE ?? 'en';
export const LANGUAGES: { code: string; label: string }[] = [
  { code: 'en', label: 'EN' },
  { code: 'ru', label: 'RU' },
];

export const SENTRY_DSN = env.VITE_SENTRY_DSN;
export const SENTRY_ENVIRONMENT = env.VITE_SENTRY_ENVIRONMENT ?? env.MODE;
export const SENTRY_SAMPLE_TRACE = Number(env.VITE_SENTRY_SAMPLE_TRACE ?? 0.1);
