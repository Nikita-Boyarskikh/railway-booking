import type { z } from 'zod';

export abstract class BaseApiError extends Error {}

export class ApiError extends BaseApiError {
  constructor(message: string, public status?: number, public data: unknown = {}) {
    super(message);
    this.name = 'ApiError';
  }
}

export class TimeoutError extends BaseApiError {
  constructor(timeoutMs: number) {
    super(`Request timed out after ${timeoutMs}ms`);
    this.name = 'TimeoutError';
  }
}

export class SchemaError extends BaseApiError {
  constructor(message: string, public issues: z.core.$ZodIssue[]) {
    super(message);
    this.name = 'SchemaError';
  }
}
