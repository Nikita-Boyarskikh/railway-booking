import type { ChangeEvent } from 'react';
import { useTranslation } from 'react-i18next';
import StationAutocomplete from '@entities/station/ui/StationAutocomplete';
import type { Station } from '@shared/api/schemas';
import { isoDate } from '@shared/lib/format';

interface Props {
  stations: Station[];
  from: string | null;
  to: string | null;
  date: Date | null;
  onFromChange: (v: string | null) => void;
  onToChange: (v: string | null) => void;
  onDateChange: (d: Date) => void;
  onSwap: () => void;
}

export default function SearchForm({
  stations, from, to, date, onFromChange, onToChange, onDateChange, onSwap,
}: Props) {
  const { t } = useTranslation();

  const handleDateChange = (event: ChangeEvent<HTMLInputElement>) => {
    const d = new Date(event.target.value);
    if (!Number.isNaN(d.valueOf())) onDateChange(d);
  };

  return (
    <div
      role="search"
      aria-label={t('a11y.searchForm')}
      className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr_1fr] gap-3 mb-6 items-center"
    >
      <label>
        <span className="sr-only">{t('search.labelFrom')}</span>
        <StationAutocomplete
          stations={stations}
          value={from}
          onChange={onFromChange}
          placeholder={t('search.placeholderFrom')}
        />
      </label>
      <button
        type="button"
        onClick={onSwap}
        disabled={!from && !to}
        aria-label={t('search.swapAria')}
        title={t('search.swap')}
        className="border border-gray-300 rounded px-3 py-2 hover:bg-gray-50 disabled:opacity-50 justify-self-center"
      >
        <span aria-hidden="true">⇄</span>
      </button>
      <label>
        <span className="sr-only">{t('search.labelTo')}</span>
        <StationAutocomplete
          stations={stations}
          value={to}
          onChange={onToChange}
          placeholder={t('search.placeholderTo')}
        />
      </label>
      <label>
        <span className="sr-only">{t('search.labelDate')}</span>
        <input
          type="date"
          min={isoDate(new Date())}
          max="9999-12-31"
          className="border border-gray-300 rounded px-3 py-2 w-full"
          value={date ? isoDate(date) : ''}
          onChange={handleDateChange}
        />
      </label>
    </div>
  );
}
