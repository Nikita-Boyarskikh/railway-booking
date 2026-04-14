import { useId } from 'react';
import { useTranslation } from 'react-i18next';
import type { SeatsForm } from '@pages/seats/model/useSeatsPage';
import { isoDate } from '@shared/lib/format';

interface Props {
  index: number;
  carNumber: number;
  seatNumber: number;
  price: string | undefined;
  form: SeatsForm;
}

export default function PassengerFormFields({
  index, carNumber, seatNumber, price, form,
}: Props) {
  const { t } = useTranslation();
  const uid = useId();
  const itemErrors = form.formState.errors.items?.[index]?.passenger;
  const inputCls = (hasError: unknown) => `border rounded px-2 py-1 w-full ${
    hasError ? 'border-red-500' : 'border-gray-300'
  }`;
  const ids = {
    name: `${uid}-name`,
    passport: `${uid}-passport`,
    gender: `${uid}-gender`,
    birth: `${uid}-birth`,
    nameErr: `${uid}-name-err`,
    passportErr: `${uid}-passport-err`,
    genderErr: `${uid}-gender-err`,
    birthErr: `${uid}-birth-err`,
  };

  return (
    <fieldset className="border rounded p-3">
      <legend className="font-medium px-1">
        {t('seats.seatHeader', { car: carNumber, seat: seatNumber, price: price ?? '' })}
      </legend>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        <div>
          <label htmlFor={ids.name} className="block text-xs text-gray-600 mb-1">
            {t('seats.fullName')}
          </label>
          <input
            id={ids.name}
            {...form.register(`items.${index}.passenger.name`)}
            minLength={1}
            maxLength={255}
            aria-invalid={Boolean(itemErrors?.name)}
            aria-describedby={itemErrors?.name ? ids.nameErr : undefined}
            className={inputCls(itemErrors?.name)}
            placeholder={t('seats.fullName')}
          />
          {itemErrors?.name && (
            <div id={ids.nameErr} className="text-xs text-red-600 mt-1">{itemErrors.name.message}</div>
          )}
        </div>
        <div>
          <label htmlFor={ids.passport} className="block text-xs text-gray-600 mb-1">
            {t('seats.passportNumber')}
          </label>
          <input
            id={ids.passport}
            {...form.register(`items.${index}.passenger.passport_number`)}
            pattern="^[A-Za-z0-9 -]+$"
            minLength={4}
            maxLength={64}
            aria-invalid={Boolean(itemErrors?.passport_number)}
            aria-describedby={itemErrors?.passport_number ? ids.passportErr : undefined}
            className={inputCls(itemErrors?.passport_number)}
            placeholder={t('seats.passportNumber')}
          />
          {itemErrors?.passport_number && (
            <div id={ids.passportErr} className="text-xs text-red-600 mt-1">{itemErrors.passport_number.message}</div>
          )}
        </div>
        <div>
          <label htmlFor={ids.gender} className="block text-xs text-gray-600 mb-1">
            {t('seats.gender')}
          </label>
          <select
            id={ids.gender}
            {...form.register(`items.${index}.passenger.gender`)}
            aria-invalid={Boolean(itemErrors?.gender)}
            aria-describedby={itemErrors?.gender ? ids.genderErr : undefined}
            className={inputCls(itemErrors?.gender)}
          >
            <option value="male">{t('seats.genderMale')}</option>
            <option value="female">{t('seats.genderFemale')}</option>
          </select>
          {itemErrors?.gender && (
            <div id={ids.genderErr} className="text-xs text-red-600 mt-1">{itemErrors.gender.message}</div>
          )}
        </div>
        <div>
          <label htmlFor={ids.birth} className="block text-xs text-gray-600 mb-1">
            {t('seats.birthDate')}
          </label>
          <input
            id={ids.birth}
            type="date"
            min="1800-01-01"
            max={isoDate(new Date())}
            {...form.register(`items.${index}.passenger.birth_date`)}
            aria-invalid={Boolean(itemErrors?.birth_date)}
            aria-describedby={itemErrors?.birth_date ? ids.birthErr : undefined}
            className={inputCls(itemErrors?.birth_date)}
          />
          {itemErrors?.birth_date && (
            <div id={ids.birthErr} className="text-xs text-red-600 mt-1">{itemErrors.birth_date.message}</div>
          )}
        </div>
      </div>
    </fieldset>
  );
}
