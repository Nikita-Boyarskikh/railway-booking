import ky, { HTTPError, TimeoutError as KyTimeoutError } from 'ky';
import Cookies from 'js-cookie';
import { z } from 'zod';
import { isoDate } from '@shared/lib/format';
import {
  DepartureSchema,
  DepartureSummarySchema,
  OrderResponseSchema,
  SeatsResponseSchema,
  StationSchema,
  type Departure,
  type DepartureSummary,
  type OrderRequest,
  type OrderResponse,
  type SeatsResponse,
  type Station,
} from './schemas';
import {CSRF_TOKEN_COOKIE, DEFAULT_API_PREFIX, DEFAULT_API_TIMEOUT_MS, UNSAFE_API_METHODS} from "@shared/config";
import {ApiError, SchemaError, TimeoutError} from "./errors";

export class ApiClient {
  private readonly http: typeof ky;
  private readonly timeoutMs: number;

  constructor(prefix: string = DEFAULT_API_PREFIX, timeoutMs: number = DEFAULT_API_TIMEOUT_MS) {
    this.timeoutMs = timeoutMs;
    this.http = ky.create({
      prefix,
      timeout: timeoutMs,
      credentials: 'same-origin',
      hooks: {
        beforeRequest: [
          ({ request }) => {
            if (UNSAFE_API_METHODS.has(request.method.toUpperCase())) {
              const csrf = Cookies.get(CSRF_TOKEN_COOKIE);
              if (csrf) request.headers.set('X-CSRFToken', csrf);
            }
          },
        ],
      },
    });
  }

  getStations(): Promise<Station[]> {
    return this.call(z.array(StationSchema), () => this.http.get('stations/').json());
  }

  searchDepartures(from: string, to: string, date: Date): Promise<DepartureSummary[]> {
    return this.call(z.array(DepartureSummarySchema), () => this.http.get('departures/', {
      searchParams: { from, to, date: isoDate(date) },
    }).json());
  }

  getDeparture(uuid: string, from: string, to: string): Promise<Departure> {
    return this.call(DepartureSchema, () => this.http.get(`departures/${encodeURIComponent(uuid)}/`, {
      searchParams: { from, to },
    }).json());
  }

  getDepartureSeats(uuid: string, from: string, to: string): Promise<SeatsResponse> {
    return this.call(SeatsResponseSchema, () => this.http.get(
      `departures/${encodeURIComponent(uuid)}/seats/`,
      { searchParams: { from, to } },
    ).json());
  }

  createOrder(payload: OrderRequest): Promise<OrderResponse> {
    return this.call(OrderResponseSchema, () => this.http.post('orders/', { json: payload }).json());
  }

  getOrder(uuid: string): Promise<OrderResponse> {
    return this.call(OrderResponseSchema, () => this.http.get(
      `orders/${encodeURIComponent(uuid)}/`,
    ).json());
  }

  private async call<Schema extends z.ZodType>(
    schema: Schema,
    fn: () => Promise<unknown>,
  ): Promise<z.infer<Schema>> {
    let raw: unknown;
    try {
      raw = await fn();
    } catch (e) {
      if (e instanceof KyTimeoutError) throw new TimeoutError(this.timeoutMs);
      if (e instanceof HTTPError) {
        const body = e.data as Record<string, unknown>;
        const rawDetail = body['detail'];
        const detail = typeof rawDetail === 'string' ? rawDetail : null;
        throw new ApiError(detail ?? e.response.statusText, e.response.status, body);
      }
      throw e;
    }
    const parsed = schema.safeParse(raw);
    if (!parsed.success) {
      throw new SchemaError('API response did not match schema', parsed.error.issues);
    }
    return parsed.data;
  }
}

export const apiClient = new ApiClient();
