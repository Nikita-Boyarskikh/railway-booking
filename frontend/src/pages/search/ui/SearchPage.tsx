import type { LoaderFunctionArgs } from 'react-router-dom';
import { useLoaderData } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { apiClient } from '@shared/api/client';
import { getCachedStations } from '@entities/station/model/stations-cache';
import type { DepartureSummary } from '@shared/api/schemas';
import SearchForm from '@widgets/search-form/ui/SearchForm';
import { DeparturesList } from '@widgets/departures-list/ui/DeparturesList';
import { useSearch } from '@features/search-departures/model/useSearch';

export async function searchLoader({ request }: LoaderFunctionArgs) {
  const url = new URL(request.url);
  const from = url.searchParams.get('from');
  const to = url.searchParams.get('to');
  const date = url.searchParams.get('date');
  const stations = await getCachedStations();
  let departures: DepartureSummary[] | null = null;
  if (from && to && date) {
    departures = await apiClient.searchDepartures(from, to, new Date(date));
  }
  return { stations, departures };
}

export default function SearchPage() {
  const { stations, departures } = useLoaderData<typeof searchLoader>();
  const { t } = useTranslation();
  const {
    from, to, date, loading,
    onFromChange, onToChange, onDateChange, onSwap, onSelect,
  } = useSearch();

  return (
    <div>
      <title>{t('search.pageTitle')}</title>
      <h1 className="text-2xl font-bold mb-4">{t('search.title')}</h1>
      <SearchForm
        stations={stations}
        from={from}
        to={to}
        date={date}
        onFromChange={onFromChange}
        onToChange={onToChange}
        onDateChange={onDateChange}
        onSwap={onSwap}
      />
      {loading && <div className="text-gray-500 mb-4">{t('search.searching')}</div>}
      {departures && <DeparturesList departures={departures} onSelect={onSelect} />}
    </div>
  );
}
