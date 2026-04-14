/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_DEFAULT_API_TIMEOUT_MS?: string;
  readonly VITE_STATIONS_CACHE_MS?: string;
  readonly VITE_DEFAULT_LOCALE?: string;
  readonly VITE_SENTRY_DSN?: string;
  readonly VITE_SENTRY_ENVIRONMENT?: string;
  readonly VITE_SENTRY_SAMPLE_TRACE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
