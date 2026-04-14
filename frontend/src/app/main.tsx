import React from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { router } from '@app/routes';
import { initSentry, Sentry } from '@app/providers/sentry';
import '@app/i18n';
import '@app/index.css';

initSentry();

const rootEl = document.getElementById('root');
if (!rootEl) throw new Error('Root element #root not found');

ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <Sentry.ErrorBoundary fallback={<div className="p-6 text-red-600">Unexpected error.</div>}>
      <RouterProvider router={router} />
    </Sentry.ErrorBoundary>
  </React.StrictMode>,
);
