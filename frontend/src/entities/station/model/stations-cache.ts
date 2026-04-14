import type { Station } from '@shared/api/schemas';
import { apiClient } from '@shared/api/client';
import { CACHE_TTL_MS } from '@shared/config';

let cache: { at: number; promise: Promise<Station[]> } | null = null;

export function getCachedStations(force = false): Promise<Station[]> {
  if (!force && cache && Date.now() - cache.at < CACHE_TTL_MS) {
    return cache.promise;
  }
  const entry = { at: Date.now(), promise: apiClient.getStations() };
  entry.promise.catch(() => {
    if (cache === entry) cache = null;
  });
  cache = entry;
  return cache.promise;
}
