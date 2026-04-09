import { useMemo, useState } from 'react';
import type { Station } from '../types';

interface Props {
  stations: Station[];
  value: number | null;
  onChange: (id: number | null) => void;
  placeholder: string;
}

export default function StationAutocomplete({
  stations, value, onChange, placeholder,
}: Props) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);

  const selected = useMemo(
    () => stations.find((s) => s.id === value) ?? null,
    [stations, value],
  );

  const display = selected ? `${selected.name} (${selected.code})` : query;

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return stations
      .filter((s) => s.name.toLowerCase().includes(q) || s.code.toLowerCase().includes(q))
      .slice(0, 8);
  }, [stations, query]);

  return (
    <div className="relative">
      <input
        className="w-full border border-gray-300 rounded px-3 py-2"
        placeholder={placeholder}
        value={display}
        onChange={(e) => {
          setQuery(e.target.value);
          onChange(null);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      />
      {open && filtered.length > 0 && (
        <ul className="absolute z-10 bg-white border border-gray-300 w-full mt-1 rounded shadow max-h-60 overflow-y-auto">
          {filtered.map((s) => (
            <li key={s.id}>
              <button
                type="button"
                className="w-full text-left px-3 py-2 hover:bg-blue-50"
                onMouseDown={() => {
                  onChange(s.id);
                  setQuery('');
                  setOpen(false);
                }}
              >
                {s.name} <span className="text-gray-500">({s.code})</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
