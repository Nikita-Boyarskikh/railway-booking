import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import type { Car, Seat } from '@shared/api/schemas';
import { seatKey } from '@entities/seat/lib/seatKey';

interface Props {
  car: Car;
  isOpen: boolean;
  onToggle: (carNumber: number) => void;
  selected: Set<string>;
  onToggleSeat: (carNumber: number, seat: Seat) => void;
}

export default function CarPanel({
  car, isOpen, onToggle, selected, onToggleSeat,
}: Props) {
  const { t } = useTranslation();
  const handleToggle = useCallback(() => { onToggle(car.number); }, [onToggle, car.number]);
  const freeCount = car.seats.filter((s) => s.status === 'free').length;
  const regionId = `car-${car.number}-seats`;

  return (
    <div className="bg-white shadow rounded">
      <button
        type="button"
        onClick={handleToggle}
        aria-expanded={isOpen}
        aria-controls={regionId}
        className="w-full flex justify-between items-center px-4 py-3 text-left hover:bg-gray-50"
      >
        <span className="font-semibold">
          {t('seats.carHeader', { number: car.number })}
          <span className="text-gray-500 font-normal">
            {t('seats.carMeta', { type: car.car_type, free: freeCount })}
          </span>
        </span>
        <span aria-hidden="true">{isOpen ? '▾' : '▸'}</span>
      </button>
      {isOpen && (
        <div id={regionId} className="px-4 pb-4">
          <table className="w-full text-sm">
            <caption className="sr-only">{t('a11y.carSeats', { number: car.number })}</caption>
            <thead className="text-left text-gray-500">
              <tr>
                <th scope="col" className="py-1">{t('seats.columns.seat')}</th>
                <th scope="col" className="py-1">{t('seats.columns.type')}</th>
                <th scope="col" className="py-1">{t('seats.columns.status')}</th>
                <th scope="col" className="py-1">{t('seats.columns.price')}</th>
                <th scope="col" className="py-1">
                  <span className="sr-only">{t('search.select')}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {car.seats.map((seat) => {
                const key = seatKey(car.number, seat.number);
                const checked = selected.has(key);
                const statusLabel = seat.status === 'free'
                  ? t('seats.statusFree')
                  : t('seats.statusOccupied');
                return (
                  <tr key={key} className="border-t">
                    <td className="py-1">{seat.number}</td>
                    <td className="py-1">{seat.seat_type}</td>
                    <td className={`py-1 ${seat.status === 'free' ? 'text-green-600' : 'text-gray-400'}`}>
                      {statusLabel}
                    </td>
                    <td className="py-1">{seat.price}</td>
                    <td className="py-1">
                      <input
                        type="checkbox"
                        aria-label={t('a11y.selectSeat', { car: car.number, seat: seat.number })}
                        disabled={seat.status !== 'free'}
                        checked={checked}
                        onChange={() => { onToggleSeat(car.number, seat); }}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
