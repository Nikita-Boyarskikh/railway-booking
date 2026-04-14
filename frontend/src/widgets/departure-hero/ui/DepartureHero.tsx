import { useTranslation } from 'react-i18next';
import type { Departure, Station } from '@shared/api/schemas';
import { formatDateTime } from '@shared/lib/format';

interface Props {
  departure: Departure;
  fromStation: Station | null;
  toStation: Station | null;
}

export default function DepartureHero({
  departure, fromStation, toStation,
}: Props) {
  const { t } = useTranslation();
  return (
    <div className="bg-white shadow rounded p-4 mb-4">
      <div className="font-semibold text-lg">
        {departure.train_number}
        {departure.train_name ? ` · ${departure.train_name}` : ''}
      </div>
      <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
        <div>
          <span className="text-gray-500">{t('seats.from')}</span>
          <span className="font-medium">{fromStation?.name ?? fromStation?.code ?? ''}</span>
          {departure.departure_time && (
            <span className="text-gray-600">
              {` · ${formatDateTime(departure.departure_time)}`}
            </span>
          )}
        </div>
        <div>
          <span className="text-gray-500">{t('seats.to')}</span>
          <span className="font-medium">{toStation?.name ?? fromStation?.code ?? ''}</span>
          {departure.arrival_time && (
            <span className="text-gray-600">
              {` · ${formatDateTime(departure.arrival_time)}`}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
