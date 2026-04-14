import { useCallback, useMemo } from 'react';
import { useFieldArray, useForm, type UseFormReturn } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { PassengerSchema } from '@shared/api/schemas';
import type { Seat, SeatsResponse } from '@shared/api/schemas';
import { seatKey as makeSeatKey } from '@entities/seat/lib/seatKey';

const SeatsFormItemSchema = z.object({
  seatKey: z.string(),
  carNumber: z.number().int().positive(),
  seatNumber: z.number().int().positive(),
  passenger: PassengerSchema,
});

const SeatsFormSchema = z.object({
  items: z.array(SeatsFormItemSchema).min(1),
});

export type SeatsFormValues = z.infer<typeof SeatsFormSchema>;
export type SeatsFormItem = z.infer<typeof SeatsFormItemSchema>;
export type SeatsForm = UseFormReturn<SeatsFormValues>;

export function useSeatsForm(seats: SeatsResponse) {
  const form = useForm<SeatsFormValues>({
    resolver: zodResolver(SeatsFormSchema),
    defaultValues: { items: [] },
    mode: 'onBlur',
  });
  const {
    fields, append, remove, replace,
  } = useFieldArray({ control: form.control, name: 'items', keyName: 'fieldId' });

  const selected = useMemo(
    () => new Set(fields.map((f) => f.seatKey)),
    [fields],
  );

  const toggleSeat = useCallback((carNumber: number, seat: Seat) => {
    if (seat.status !== 'free') return;
    const key = makeSeatKey(carNumber, seat.number);
    const idx = fields.findIndex((f) => f.seatKey === key);
    if (idx >= 0) {
      remove(idx);
      return;
    }
    append({
      seatKey: key,
      carNumber,
      seatNumber: seat.number,
      passenger: {
        name: '', passport_number: '', gender: 'male', birth_date: '',
      },
    });
  }, [fields, append, remove]);

  const pruneOccupied = useCallback(() => {
    const freeKeys = new Set<string>();
    seats.cars.forEach((c) => {
      c.seats.forEach((s) => {
        if (s.status === 'free') freeKeys.add(makeSeatKey(c.number, s.number));
      });
    });
    const kept = fields
      .filter((f) => freeKeys.has(f.seatKey))
      .map((f): SeatsFormItem => ({
        seatKey: f.seatKey,
        carNumber: f.carNumber,
        seatNumber: f.seatNumber,
        passenger: f.passenger,
      }));
    if (kept.length !== fields.length) replace(kept);
  }, [seats, fields, replace]);

  return {
    form, fields, selected, toggleSeat, pruneOccupied,
  };
}
