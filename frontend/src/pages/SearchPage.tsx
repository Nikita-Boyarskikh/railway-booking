import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStations, searchDepartures } from '../api/client';
import StationAutocomplete from '../components/StationAutocomplete';
import type { DepartureSummary, Station } from '../types';

export default function SearchPage() {
  const navigate = useNavigate();
  const [stations, setStations] = useState<Station[]>([]);
  const [from, setFrom] = useState<number | null>(null);
  const [to, setTo] = useState<number | null>(null);
  const [date, setDate] = useState('');
  const [results, setResults] = useState<DepartureSummary[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getStations().then(setStations).catch((e) => setError(e.message));
  }, []);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestIdRef = useRef(0);

  const runSearch = (
    nextFrom: number | null,
    nextTo: number | null,
    nextDate: string,
  ) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!nextFrom || !nextTo || !nextDate) {
      setResults(null);
      setLoading(false);
      return;
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    debounceRef.current = setTimeout(() => {
      setLoading(true);
      setError(null);
      searchDepartures(nextFrom, nextTo, nextDate)
        .then((r) => {
          if (requestIdRef.current === requestId) setResults(r);
        })
        .catch((err) => {
          if (requestIdRef.current === requestId) setError((err as Error).message);
        })
        .finally(() => {
          if (requestIdRef.current === requestId) setLoading(false);
        });
    }, 300);
  };

  const onFromChange = (v: number | null) => {
    setFrom(v);
    runSearch(v, to, date);
  };
  const onToChange = (v: number | null) => {
    setTo(v);
    runSearch(from, v, date);
  };
  const onDateChange = (v: string) => {
    setDate(v);
    runSearch(from, to, v);
  };

  const onSelect = (dep: DepartureSummary) => {
    const fromStation = stations.find((s) => s.id === from) ?? null;
    const toStation = stations.find((s) => s.id === to) ?? null;
    navigate(`/departures/${dep.departure_id}/seats?from=${from}&to=${to}`, {
      state: { departure: dep, date, fromStation, toStation },
    });
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Find a train</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
        <StationAutocomplete
          stations={stations}
          value={from}
          onChange={onFromChange}
          placeholder="From"
        />
        <StationAutocomplete
          stations={stations}
          value={to}
          onChange={onToChange}
          placeholder="To"
        />
        <input
          type="date"
          className="border border-gray-300 rounded px-3 py-2"
          value={date}
          onChange={(e) => onDateChange(e.target.value)}
        />
      </div>

      {loading && <div className="text-gray-500 mb-4">Searching…</div>}
      {error && <div className="text-red-600 mb-4">{error}</div>}

      {results && results.length === 0 && (
        <div className="text-gray-600">No departures found.</div>
      )}

      {results && results.length > 0 && (
        <table className="w-full bg-white shadow rounded overflow-hidden">
          <thead className="bg-gray-100 text-left">
            <tr>
              <th className="px-4 py-2">Train</th>
              <th className="px-4 py-2">Departure</th>
              <th className="px-4 py-2">Arrival</th>
              <th className="px-4 py-2">Free seats</th>
              <th className="px-4 py-2">From</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {results.map((d) => (
              <tr key={d.departure_id} className="border-t">
                <td className="px-4 py-2">
                  {d.train_number}
                  {' '}
                  {d.train_name}
                </td>
                <td className="px-4 py-2">{d.departure_time}</td>
                <td className="px-4 py-2">{d.arrival_time}</td>
                <td className="px-4 py-2">{d.free_seat_count}</td>
                <td className="px-4 py-2">
                  {d.min_price ? `$${d.min_price}` : '—'}
                </td>
                <td className="px-4 py-2">
                  <button
                    type="button"
                    className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 disabled:opacity-50"
                    onClick={() => onSelect(d)}
                    disabled={d.free_seat_count === 0}
                  >
                    Select
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
