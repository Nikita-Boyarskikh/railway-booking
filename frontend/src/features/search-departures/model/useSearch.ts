import { useCallback } from 'react';
import { useNavigate, useNavigation, useSearchParams } from 'react-router-dom';
import type { DepartureSummary } from '@shared/api/schemas';
import { isoDate } from '@shared/lib/format';

export interface UseSearchResult {
  from: string | null;
  to: string | null;
  date: Date | null;
  loading: boolean;
  onFromChange: (v: string | null) => void;
  onToChange: (v: string | null) => void;
  onDateChange: (d: Date) => void;
  onSwap: () => void;
  onSelect: (dep: DepartureSummary) => void;
}

export function useSearch(): UseSearchResult {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const navigation = useNavigation();

  const from = searchParams.get('from');
  const to = searchParams.get('to');
  const dateStr = searchParams.get('date');
  const date = dateStr ? new Date(dateStr) : null;
  const loading = navigation.state === 'loading';

  const patchParams = useCallback((patch: Record<string, string | null | undefined>) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      Object.entries(patch).forEach(([k, v]) => {
        if (v == null || v === '') next.delete(k);
        else next.set(k, v);
      });
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  const onFromChange = useCallback((v: string | null) => { patchParams({ from: v }); }, [patchParams]);
  const onToChange = useCallback((v: string | null) => { patchParams({ to: v }); }, [patchParams]);
  const onDateChange = useCallback((d: Date) => { patchParams({ date: isoDate(d) }); }, [patchParams]);
  const onSwap = useCallback(() => { patchParams({ from: to, to: from }); }, [patchParams, from, to]);
  const onSelect = useCallback((dep: DepartureSummary) => {
    if (from && to) void navigate(`/departures/${dep.uuid}/seats?from=${from}&to=${to}`);
  }, [navigate, from, to]);

  return {
    from, to, date, loading, onFromChange, onToChange, onDateChange, onSwap, onSelect,
  };
}
