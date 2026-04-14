import * as Sentry from '@sentry/react';
import { SENTRY_DSN, SENTRY_ENVIRONMENT, SENTRY_SAMPLE_TRACE } from '@shared/config';

export function initSentry() {
  if (!SENTRY_DSN) return;
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: SENTRY_ENVIRONMENT,
    tracesSampleRate: SENTRY_SAMPLE_TRACE,
    integrations: [Sentry.browserTracingIntegration()],
  });
}

export { Sentry };
