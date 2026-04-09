import { useEffect, useMemo, useState } from 'react';
import {
  useLocation, useNavigate, useParams, useSearchParams,
} from 'react-router-dom';
import { createOrder, getDepartureSeats } from '../api/client';
import type {
  Car, DepartureSummary, OrderItem, Seat, SeatsResponse, Station,
} from '../types';

interface SeatsLocationState {
  departure?: DepartureSummary;
  date?: string;
  fromStation?: Station | null;
  toStation?: Station | null;
}

interface PassengerForm {
  passenger_name: string;
  passenger_passport: string;
  passenger_gender: 'male' | 'female';
  passenger_birth_date: string;
}

const emptyForm = (): PassengerForm => ({
  passenger_name: '',
  passenger_passport: '',
  passenger_gender: 'male',
  passenger_birth_date: '',
});

const seatKey = (carNumber: number, seatNumber: number) => `${carNumber}:${seatNumber}`;

export default function SeatsPage() {
  const { id } = useParams<{ id: string }>();
  const [params] = useSearchParams();
  const fromCode = params.get('from') ?? '';
  const toCode = params.get('to') ?? '';
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as SeatsLocationState;
  const { departure, date, fromStation, toStation } = state;

  const [data, setData] = useState<SeatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openCars, setOpenCars] = useState<Set<number>>(new Set());
  const [selected, setSelected] = useState<Map<string, PassengerForm>>(new Map());
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!id || !fromCode || !toCode) return;
    getDepartureSeats(id, fromCode, toCode)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [id, fromCode, toCode]);

  const seatPriceByKey = useMemo(() => {
    const m = new Map<string, string>();
    data?.cars.forEach((c) => c.seats.forEach((s) => m.set(seatKey(c.number, s.number), s.price)));
    return m;
  }, [data]);

  const total = useMemo(() => {
    let sum = 0;
    selected.forEach((_v, key) => {
      sum += Number(seatPriceByKey.get(key) ?? 0);
    });
    return sum.toFixed(2);
  }, [selected, seatPriceByKey]);

  const toggleCar = (carNumber: number) => {
    setOpenCars((prev) => {
      const next = new Set(prev);
      if (next.has(carNumber)) next.delete(carNumber);
      else next.add(carNumber);
      return next;
    });
  };

  const toggleSeat = (carNumber: number, seat: Seat) => {
    if (seat.status !== 'free') return;
    const key = seatKey(carNumber, seat.number);
    setSelected((prev) => {
      const next = new Map(prev);
      if (next.has(key)) next.delete(key);
      else next.set(key, emptyForm());
      return next;
    });
  };

  const updateForm = (key: string, patch: Partial<PassengerForm>) => {
    setSelected((prev) => {
      const next = new Map(prev);
      const cur = next.get(key);
      if (cur) next.set(key, { ...cur, ...patch });
      return next;
    });
  };

  const canBook = selected.size > 0 && Array.from(selected.values()).every(
    (f) => f.passenger_name && f.passenger_passport && f.passenger_birth_date,
  );

  const onBook = async () => {
    if (!id) return;
    setSubmitting(true);
    setError(null);
    const items: OrderItem[] = Array.from(selected.entries()).map(([key, f]) => {
      const [carStr, seatStr] = key.split(':');
      return {
        car_number: Number(carStr),
        seat_number: Number(seatStr),
        ...f,
      };
    });
    try {
      const order = await createOrder({
        departure_uuid: id,
        station_from_code: fromCode,
        station_to_code: toCode,
        items,
      });
      navigate(`/orders/${order.uuid}`, { state: { order } });
    } catch (e) {
      const err = e as Error & { status?: number };
      if (err.status === 409) {
        setError('Seat no longer available. Please refresh and try again.');
      } else {
        setError(err.message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (!data) return <div>Loading…</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Select seats</h1>
      {departure && (
        <div className="bg-white shadow rounded p-4 mb-4">
          <div className="font-semibold text-lg">
            {departure.train_number}
            {departure.train_name ? ` · ${departure.train_name}` : ''}
          </div>
          {date && <div className="text-sm text-gray-500">{date}</div>}
          <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-gray-500">From: </span>
              <span className="font-medium">
                {fromStation?.name ?? fromCode}
              </span>
              {departure.departure_time && (
                <span className="text-gray-600">
                  {' · '}
                  {departure.departure_time}
                </span>
              )}
            </div>
            <div>
              <span className="text-gray-500">To: </span>
              <span className="font-medium">
                {toStation?.name ?? toCode}
              </span>
              {departure.arrival_time && (
                <span className="text-gray-600">
                  {' · '}
                  {departure.arrival_time}
                </span>
              )}
            </div>
          </div>
        </div>
      )}
      {error && <div className="text-red-600 mb-4">{error}</div>}

      <div className="space-y-3">
        {data.cars.map((car: Car) => {
          const isOpen = openCars.has(car.number);
          const freeCount = car.seats.filter((s) => s.status === 'free').length;
          return (
            <div key={car.number} className="bg-white shadow rounded">
              <button
                type="button"
                onClick={() => toggleCar(car.number)}
                className="w-full flex justify-between items-center px-4 py-3 text-left hover:bg-gray-50"
              >
                <span className="font-semibold">
                  Car
                  {' '}
                  {car.number}
                  {' '}
                  <span className="text-gray-500 font-normal">
                    (
                    {car.car_type}
                    ,
                    {' '}
                    {freeCount}
                    {' '}
                    free)
                  </span>
                </span>
                <span>{isOpen ? '▾' : '▸'}</span>
              </button>
              {isOpen && (
                <div className="px-4 pb-4">
                  <table className="w-full text-sm">
                    <thead className="text-left text-gray-500">
                      <tr>
                        <th className="py-1">Seat</th>
                        <th className="py-1">Type</th>
                        <th className="py-1">Status</th>
                        <th className="py-1">Price</th>
                        <th className="py-1" />
                      </tr>
                    </thead>
                    <tbody>
                      {car.seats.map((seat) => {
                        const key = seatKey(car.number, seat.number);
                        const checked = selected.has(key);
                        return (
                          <tr key={key} className="border-t">
                            <td className="py-1">{seat.number}</td>
                            <td className="py-1">{seat.seat_type}</td>
                            <td className={`py-1 ${seat.status === 'free' ? 'text-green-600' : 'text-gray-400'}`}>
                              {seat.status}
                            </td>
                            <td className="py-1">{seat.price}</td>
                            <td className="py-1">
                              <input
                                type="checkbox"
                                disabled={seat.status !== 'free'}
                                checked={checked}
                                onChange={() => toggleSeat(car.number, seat)}
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
        })}
      </div>

      {selected.size > 0 && (
        <div className="mt-6 bg-white shadow rounded p-4">
          <h2 className="font-semibold mb-3">Passenger details</h2>
          <div className="space-y-4">
            {Array.from(selected.entries()).map(([key, form]) => {
              const [carStr, seatStr] = key.split(':');
              return (
                <div key={key} className="border rounded p-3">
                  <div className="font-medium mb-2">
                    {`Car ${carStr} · Seat ${seatStr}`}
                    {' — $'}
                    {seatPriceByKey.get(key)}
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    <input
                      className="border rounded px-2 py-1"
                      placeholder="Full name"
                      value={form.passenger_name}
                      onChange={(e) => updateForm(key, { passenger_name: e.target.value })}
                    />
                    <input
                      className="border rounded px-2 py-1"
                      placeholder="Passport number"
                      value={form.passenger_passport}
                      onChange={(e) => updateForm(key, { passenger_passport: e.target.value })}
                    />
                    <select
                      className="border rounded px-2 py-1"
                      value={form.passenger_gender}
                      onChange={(e) => updateForm(key, {
                        passenger_gender: e.target.value as 'male' | 'female',
                      })}
                    >
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                    </select>
                    <input
                      type="date"
                      className="border rounded px-2 py-1"
                      value={form.passenger_birth_date}
                      onChange={(e) => updateForm(key, { passenger_birth_date: e.target.value })}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="mt-6 flex justify-between items-center">
        <div className="text-lg font-semibold">
          Total:
          {' '}
          {total}
        </div>
        <button
          type="button"
          className="bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700 disabled:opacity-50"
          disabled={!canBook || submitting}
          onClick={onBook}
        >
          {submitting ? 'Booking…' : 'Book'}
        </button>
      </div>
    </div>
  );
}