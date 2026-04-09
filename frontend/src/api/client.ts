import type {
  DepartureSummary, OrderRequest, OrderResponse, SeatsResponse, Station,
} from '../types';

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err = new Error(body.detail || res.statusText) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return res.json() as Promise<T>;
}

export const getStations = () => http<Station[]>('/api/stations/');

export const searchDepartures = (from: number, to: number, date: string) =>
  http<DepartureSummary[]>(`/api/departures/?from=${from}&to=${to}&date=${date}`);

export const getDepartureSeats = (id: number, from: number, to: number) =>
  http<SeatsResponse>(`/api/departures/${id}/seats/?from=${from}&to=${to}`);

export const createOrder = (payload: OrderRequest) =>
  http<OrderResponse>('/api/orders/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const getOrder = (id: number) => http<OrderResponse>(`/api/orders/${id}/`);
