import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import type { OrderResponse } from '@shared/api/schemas';
import { formatMoney } from '@shared/lib/format';

interface Props {
  order: OrderResponse;
}

export default function ConfirmationView({ order }: Props) {
  const { t } = useTranslation();
  return (
    <div>
      <title>{t('confirmation.pageTitle')}</title>
      <h1 className="text-2xl font-bold mb-2 text-green-700">{t('confirmation.title')}</h1>
      <p className="text-gray-600 mb-6">
        {t('confirmation.orderSummary', { uuid: order.uuid })}
        <span className="font-semibold">{formatMoney(parseFloat(order.total_price), order.total_price_currency)}</span>
      </p>

      <table className="w-full bg-white shadow rounded overflow-hidden">
        <caption className="sr-only">{t('a11y.bookingSummary')}</caption>
        <thead className="bg-gray-100 text-left">
          <tr>
            <th scope="col" className="px-4 py-2">{t('confirmation.columns.car')}</th>
            <th scope="col" className="px-4 py-2">{t('confirmation.columns.seat')}</th>
            <th scope="col" className="px-4 py-2">{t('confirmation.columns.from')}</th>
            <th scope="col" className="px-4 py-2">{t('confirmation.columns.to')}</th>
            <th scope="col" className="px-4 py-2">{t('confirmation.columns.passenger')}</th>
            <th scope="col" className="px-4 py-2">{t('confirmation.columns.passport')}</th>
          </tr>
        </thead>
        <tbody>
          {order.bookings.map((b) => (
            <tr key={`${b.departure_uuid}-${b.car_number}-${b.seat_number}`} className="border-t">
              <td className="px-4 py-2">{b.car_number}</td>
              <td className="px-4 py-2">{b.seat_number}</td>
              <td className="px-4 py-2">{b.station_from_code}</td>
              <td className="px-4 py-2">{b.station_to_code}</td>
              <td className="px-4 py-2">{b.passenger.name}</td>
              <td className="px-4 py-2">{b.passenger.passport_number}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-6">
        <Link to="/" className="text-blue-600 hover:underline">{t('confirmation.bookAnother')}</Link>
      </div>
    </div>
  );
}
