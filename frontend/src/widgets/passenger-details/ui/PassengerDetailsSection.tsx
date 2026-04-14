import { useTranslation } from 'react-i18next';
import type { SeatsForm, SeatsFormValues } from '@pages/seats/model/useSeatsPage';
import { parseSeatKey } from '@entities/seat/lib/seatKey';
import PassengerFormFields from '@entities/passenger/ui/PassengerFormFields';

interface Props {
  fields: (SeatsFormValues['items'][number] & { fieldId: string })[];
  seatPriceByKey: Map<string, string>;
  form: SeatsForm;
}

export default function PassengerDetailsSection({ fields, seatPriceByKey, form }: Props) {
  const { t } = useTranslation();
  if (fields.length === 0) return null;
  return (
    <div className="mt-6 bg-white shadow rounded p-4">
      <h2 className="font-semibold mb-3">{t('seats.passengerDetails')}</h2>
      <div className="space-y-4">
        {fields.map((f, index) => {
          const { carNumber, seatNumber } = parseSeatKey(f.seatKey);
          return (
            <PassengerFormFields
              key={f.fieldId}
              index={index}
              carNumber={carNumber}
              seatNumber={seatNumber}
              price={seatPriceByKey.get(f.seatKey)}
              form={form}
            />
          );
        })}
      </div>
    </div>
  );
}
