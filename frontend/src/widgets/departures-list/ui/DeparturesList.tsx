import React from 'react';
import { useTranslation } from 'react-i18next';
import { formatDateTime } from '@shared/lib/format';
import type { DepartureSummary } from '@shared/api/schemas';

interface DeparturesListRowProps {
  departure: DepartureSummary;
  onSelect: (departure: DepartureSummary) => void;
}

const DeparturesListRow: React.FC<DeparturesListRowProps> = ({ departure, onSelect }) => {
  const { t } = useTranslation();
  const handleClick = React.useCallback(() => {
    onSelect(departure);
  }, [onSelect, departure]);

  return (
    <tr className="border-t">
      <td className="px-4 py-2">
        {departure.train_number}
        {' '}
        {departure.train_name}
      </td>
      <td className="px-4 py-2">{formatDateTime(departure.departure_time)}</td>
      <td className="px-4 py-2">{formatDateTime(departure.arrival_time)}</td>
      <td className="px-4 py-2">{departure.free_seat_count}</td>
      <td className="px-4 py-2">
        {departure.min_price ?? '—'}
      </td>
      <td className="px-4 py-2">
        <button
          type="button"
          className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 disabled:opacity-50"
          onClick={handleClick}
          disabled={departure.free_seat_count === 0}
        >
          {t('search.select')}
        </button>
      </td>
    </tr>
  );
};

export interface DeparturesListProps {
  departures: DepartureSummary[];
  onSelect: (departure: DepartureSummary) => void;
}

export const DeparturesList: React.FC<DeparturesListProps> = ({ departures, onSelect }) => {
  const { t } = useTranslation();

  if (departures.length === 0) {
    return (
      <div role="status" className="text-gray-600">{t('search.noResults')}</div>
    );
  }

  return (
    <table className="w-full bg-white shadow rounded overflow-hidden">
      <caption className="sr-only">{t('a11y.searchResults')}</caption>
      <thead className="bg-gray-100 text-left">
        <tr>
          <th scope="col" className="px-4 py-2">{t('search.columns.train')}</th>
          <th scope="col" className="px-4 py-2">{t('search.columns.departure')}</th>
          <th scope="col" className="px-4 py-2">{t('search.columns.arrival')}</th>
          <th scope="col" className="px-4 py-2">{t('search.columns.freeSeats')}</th>
          <th scope="col" className="px-4 py-2">{t('search.columns.from')}</th>
          <th scope="col" className="px-4 py-2">
            <span className="sr-only">{t('search.select')}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {departures.map((departure) => (
          <DeparturesListRow key={departure.uuid} departure={departure} onSelect={onSelect} />
        ))}
      </tbody>
    </table>
  );
};
