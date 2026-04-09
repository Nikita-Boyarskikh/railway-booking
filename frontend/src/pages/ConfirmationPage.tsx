import { useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { getOrder } from '../api/client';
import type { OrderResponse } from '../types';

export default function ConfirmationPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation() as { state?: { order?: OrderResponse } };
  const [order, setOrder] = useState<OrderResponse | null>(location.state?.order ?? null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (order || !id) return;
    getOrder(Number(id)).then(setOrder).catch((e) => setError(e.message));
  }, [id, order]);

  if (error) return <div className="text-red-600">{error}</div>;
  if (!order) return <div>Loading…</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2 text-green-700">Booking confirmed</h1>
      <p className="text-gray-600 mb-6">
        Order #
        {order.id}
        {' '}
        —
        {' '}
        Total:
        {' '}
        <span className="font-semibold">{order.total_price}</span>
      </p>

      <table className="w-full bg-white shadow rounded overflow-hidden">
        <thead className="bg-gray-100 text-left">
          <tr>
            <th className="px-4 py-2">Booking</th>
            <th className="px-4 py-2">Seat</th>
            <th className="px-4 py-2">Passenger</th>
            <th className="px-4 py-2">Passport</th>
          </tr>
        </thead>
        <tbody>
          {order.bookings.map((b) => (
            <tr key={b.id} className="border-t">
              <td className="px-4 py-2">
                #
                {b.id}
              </td>
              <td className="px-4 py-2">{b.seat}</td>
              <td className="px-4 py-2">{b.passenger.name}</td>
              <td className="px-4 py-2">{b.passenger.passport_number}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="mt-6">
        <Link to="/" className="text-blue-600 hover:underline">Book another trip</Link>
      </div>
    </div>
  );
}
