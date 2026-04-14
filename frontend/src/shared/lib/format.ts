import {DEFAULT_CURRENCY} from "@shared/config";

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function parseCurrencySymbol(symbol: string): string {
  return {
    '$': 'USD'
  }[symbol] ?? DEFAULT_CURRENCY;
}

export function parseMoney(value: string | null | undefined): [number, string] {
  if (!value) return [0, DEFAULT_CURRENCY];
  const symbolMatch = /^[^0-9.-]+/.exec(value);
  const symbol = symbolMatch ? symbolMatch[0].trim() : '';
  const numeric = value.replace(/[^0-9.-]/g, '');
  const n = Number(numeric);
  return Number.isNaN(n) ? [0, DEFAULT_CURRENCY] : [n, parseCurrencySymbol(symbol)];
}

export function formatMoney(amount: number, currency = DEFAULT_CURRENCY): string {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency,
  }).format(amount);
}

export function isoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}