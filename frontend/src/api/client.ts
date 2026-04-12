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

export const getStations = () => http<Station[]>('/api/v1/stations/');

export const searchDepartures = (from: string, to: string, date: string) =>
  http<DepartureSummary[]>(`/api/v1/departures/?from=${from}&to=${to}&date=${date}`);

export const getDepartureSeats = (uuid: string, from: string, to: string) =>
  http<SeatsResponse>(`/api/v1/departures/${uuid}/seats/?from=${from}&to=${to}`);

export const createOrder = (payload: OrderRequest) =>
  http<OrderResponse>('/api/v1/orders/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const getOrder = (uuid: string) => http<OrderResponse>(`/api/v1/orders/${uuid}/`);