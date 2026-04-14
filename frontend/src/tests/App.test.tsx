import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';

vi.mock('@shared/api/client', () => ({
  apiClient: {
    getStations: vi.fn().mockResolvedValue([]),
    searchDepartures: vi.fn(),
    getDeparture: vi.fn(),
    getDepartureSeats: vi.fn(),
    createOrder: vi.fn(),
    getOrder: vi.fn(),
  },
}));

vi.mock('@shared/api/errors', () => ({
  ApiError: class ApiError extends Error {},
  TimeoutError: class TimeoutError extends Error {},
  SchemaError: class SchemaError extends Error {},
}));

vi.mock('@entities/station/model/stations-cache', () => ({
  getCachedStations: vi.fn().mockResolvedValue([]),
}));

describe('App', () => {
  it('renders without crashing', async () => {
    const { router } = await import('@app/routes');
    const memoryRouter = createMemoryRouter(router.routes, { initialEntries: ['/'] });
    const { container } = render(<RouterProvider router={memoryRouter} />);
    expect(container).toBeTruthy();
  });
});
