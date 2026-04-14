import { useTranslation } from 'react-i18next';

interface Props {
  total: string;
  canBook: boolean;
  isSubmitting: boolean;
}

export default function SeatsActionBar({ total, canBook, isSubmitting }: Props) {
  const { t } = useTranslation();
  return (
    <div className="mt-6 flex justify-between items-center">
      <div className="text-lg font-semibold">{t('seats.total', { total })}</div>
      <button
        type="submit"
        className="bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700 disabled:opacity-50"
        disabled={!canBook || isSubmitting}
      >
        {isSubmitting ? t('seats.booking') : t('seats.book')}
      </button>
    </div>
  );
}
