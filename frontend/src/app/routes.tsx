import { createBrowserRouter, useRouteError } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import RootLayout from '@widgets/layout/ui/RootLayout';
import NotFoundPage from '@pages/not-found/ui/NotFoundPage';
import ErrorPage from '@pages/error/ui/ErrorPage';
import { ApiError } from '@shared/api/errors';

function RouteErrorBoundary() {
  const error = useRouteError();
  const { t } = useTranslation();
  if (error instanceof ApiError && error.status === 404) {
    return <NotFoundPage />;
  }
  const message = error instanceof Error ? error.message : t('error.fallback');
  return <ErrorPage header={t('error.header')} message={message} />;
}

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    errorElement: <RouteErrorBoundary />,
    children: [
      {
        index: true,
        lazy: async () => {
          const mod = await import('@pages/search/ui/SearchPage');
          return { Component: mod.default, loader: mod.searchLoader };
        },
      },
      {
        path: 'departures/:id/seats',
        lazy: async () => {
          const mod = await import('@pages/seats/ui/SeatsPage');
          return { Component: mod.default, loader: mod.seatsLoader };
        },
      },
      {
        path: 'orders/:id',
        lazy: async () => {
          const mod = await import('@pages/confirmation/ui/ConfirmationPage');
          return { Component: mod.default, loader: mod.orderLoader };
        },
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
