import { useState } from 'react';
import { useNavigate, useRevalidator } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { apiClient } from '@shared/api/client';
import { ApiError } from '@shared/api/errors';
import { parseValidationErrors } from '@shared/lib/validation';
import type { SeatsForm, SeatsFormValues } from '@features/select-seat/model/useSeatsForm';

interface UseOrderSubmitOptions {
  form: SeatsForm;
  totalAmount: number;
  departureUuid: string;
  fromCode: string;
  toCode: string;
  onConflict: () => void;
}

export function useOrderSubmit({
  form, totalAmount, departureUuid, fromCode, toCode, onConflict,
}: UseOrderSubmitOptions) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const revalidator = useRevalidator();
  const [topError, setTopError] = useState<string | null>(null);

  const submit = form.handleSubmit(async (values: SeatsFormValues) => {
    setTopError(null);
    try {
      const order = await apiClient.createOrder({
        departure_uuid: departureUuid,
        station_from_code: fromCode,
        station_to_code: toCode,
        items: values.items.map((i) => ({
          car_number: i.carNumber,
          seat_number: i.seatNumber,
          passenger: i.passenger,
        })),
        expected_total_price: totalAmount.toFixed(2),
      });
      void navigate(`/orders/${order.uuid}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 400) {
        const flat = parseValidationErrors(e.data);
        const topErrors: string[] = [];
        Object.entries(flat).forEach(([path, msg]) => {
          if (path.startsWith('items.')) {
            form.setError(path as never, { message: msg });
          } else {
            topErrors.push(path ? `${path}: ${msg}` : msg);
          }
        });
        if (topErrors.length) setTopError(topErrors.join(' · '));
        return;
      }
      if (e instanceof ApiError && e.status === 409) {
        void revalidator.revalidate();
        onConflict();
        setTopError(e.message || t('seats.seatConflict'));
        return;
      }
      setTopError(e instanceof Error ? e.message : t('seats.submitFailed'));
    }
  });

  return { submit, topError, isSubmitting: form.formState.isSubmitting };
}
