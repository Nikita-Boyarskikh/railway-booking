import type { Departure, SeatsResponse, Station } from '@shared/api/schemas';
import { useSeatsForm } from '@features/select-seat/model/useSeatsForm';
import { useSeatPricing } from '@features/select-seat/model/useSeatPricing';
import { useOrderSubmit } from '@features/book-order/model/useOrderSubmit';
import { useToggleSet } from '@shared/lib/useToggleSet';

export type { SeatsForm, SeatsFormValues, SeatsFormItem } from '@features/select-seat/model/useSeatsForm';

export interface SeatsPageData {
  departure: Departure;
  seats: SeatsResponse;
  fromStation: Station | null;
  toStation: Station | null;
}

export function useSeatsPage(data: SeatsPageData) {
  const {
    form, fields, selected, toggleSeat, pruneOccupied,
  } = useSeatsForm(data.seats);

  const { seatPriceByKey, totalAmount, total } = useSeatPricing(data.seats, fields);

  const [openCars, toggleCar] = useToggleSet<number>();

  const { submit, topError, isSubmitting } = useOrderSubmit({
    form,
    totalAmount,
    departureUuid: data.departure.uuid,
    fromCode: data.fromStation?.code ?? '',
    toCode: data.toStation?.code ?? '',
    onConflict: pruneOccupied,
  });

  return {
    departure: data.departure,
    cars: data.seats.cars,
    fromStation: data.fromStation,
    toStation: data.toStation,
    openCars,
    toggleCar,
    selected,
    toggleSeat,
    fields,
    form,
    seatPriceByKey,
    total,
    canBook: fields.length > 0,
    isSubmitting,
    topError,
    onSubmit: submit,
  };
}
