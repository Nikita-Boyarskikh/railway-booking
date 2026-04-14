import { useMemo } from 'react';
import { DEFAULT_CURRENCY } from '@shared/config';
import { formatMoney, parseMoney } from '@shared/lib/format';
import { seatKey as makeSeatKey } from '@entities/seat/lib/seatKey';
import type { SeatsResponse } from '@shared/api/schemas';

interface HasSeatKey { seatKey: string }

export function useSeatPricing(seats: SeatsResponse, selected: readonly HasSeatKey[]) {
  const seatPriceByKey = useMemo(() => {
    const m = new Map<string, string>();
    seats.cars.forEach((c) => {
      c.seats.forEach((s) => m.set(makeSeatKey(c.number, s.number), s.price));
    });
    return m;
  }, [seats]);

  const [totalAmount, totalCurrency] = useMemo(() => {
    let sum = 0;
    let currency = DEFAULT_CURRENCY;
    selected.forEach((f) => {
      const [amount, ccy] = parseMoney(seatPriceByKey.get(f.seatKey));
      sum += amount;
      currency = ccy;
    });
    return [sum, currency] as const;
  }, [selected, seatPriceByKey]);

  const total = useMemo(
    () => formatMoney(totalAmount, totalCurrency),
    [totalAmount, totalCurrency],
  );

  return {
    seatPriceByKey, totalAmount, totalCurrency, total,
  };
}
