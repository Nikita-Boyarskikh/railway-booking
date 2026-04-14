import { useMemo, useState } from 'react';
import {
  Combobox, ComboboxButton, ComboboxInput, ComboboxOption, ComboboxOptions,
} from '@headlessui/react';
import { useTranslation } from 'react-i18next';
import type { Station } from '@shared/api/schemas';

interface Props {
  stations: Station[];
  value: string | null;
  onChange: (code: string | null) => void;
  placeholder: string;
}

export default function StationAutocomplete({
  stations, value, onChange, placeholder,
}: Props) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');

  const selected = useMemo(
    () => stations.find((s) => s.code === value) ?? null,
    [stations, value],
  );

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    if (!q) return stations.slice(0, 8);
    return stations
      .filter((s) => s.name.toLowerCase().includes(q) || s.code.toLowerCase().includes(q))
      .slice(0, 8);
  }, [stations, query]);

  const displayValue = (s: Station | null) => (s ? `${s.name} (${s.code})` : '');

  return (
    <Combobox
      value={selected}
      onChange={(s: Station | null) => {
        onChange(s?.code ?? null);
        setQuery('');
      }}
      immediate
    >
      <div className="relative">
        <ComboboxInput
          className="w-full border border-gray-300 rounded px-3 py-2"
          placeholder={placeholder}
          displayValue={displayValue}
          onFocus={(e) => { e.currentTarget.select(); }}
          onChange={(e) => {
            setQuery(e.target.value);
            if (e.target.value === '') onChange(null);
          }}
        />
        <ComboboxButton className="sr-only" aria-label={t('seats.openStations')} />
        <ComboboxOptions
          className="absolute z-10 bg-white border border-gray-300 w-full mt-1 rounded shadow max-h-60 overflow-y-auto"
        >
          {filtered.map((s) => (
            <ComboboxOption
              key={s.code}
              value={s}
              className="w-full text-left px-3 py-2 cursor-pointer data-focus:bg-blue-100 data-selected:bg-blue-50"
            >
              {s.name} <span className="text-gray-500">({s.code})</span>
            </ComboboxOption>
          ))}
        </ComboboxOptions>
      </div>
    </Combobox>
  );
}
