import type { LoaderFunctionArgs } from 'react-router-dom';
import { useLoaderData } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { apiClient } from '@shared/api/client';
import { getCachedStations } from '@entities/station/model/stations-cache';
import DepartureHero from '@widgets/departure-hero/ui/DepartureHero';
import SeatsList from '@widgets/seats-list/ui/SeatsList';
import PassengerDetailsSection from '@widgets/passenger-details/ui/PassengerDetailsSection';
import SeatsActionBar from '@widgets/seats-action-bar/ui/SeatsActionBar';
import { useSeatsPage } from '@pages/seats/model/useSeatsPage';

export async function seatsLoader({ params, request }: LoaderFunctionArgs) {
  const uuid = params['id'];
  if (!uuid) throw new Response('Missing id', { status: 400 });
  const url = new URL(request.url);
  const fromCode = url.searchParams.get('from') ?? '';
  const toCode = url.searchParams.get('to') ?? '';

  const [departure, seats, stations] = await Promise.all([
    apiClient.getDeparture(uuid, fromCode, toCode),
    apiClient.getDepartureSeats(uuid, fromCode, toCode),
    getCachedStations(),
  ]);

  return {
    departure,
    seats,
    fromStation: stations.find((s) => s.code === fromCode) ?? null,
    toStation: stations.find((s) => s.code === toCode) ?? null,
  };
}

export default function SeatsPage() {
  const data = useLoaderData<typeof seatsLoader>();
  const { t } = useTranslation();
  const vm = useSeatsPage(data);

  return (
    <form onSubmit={vm.onSubmit}>
      <title>{t('seats.pageTitle')}</title>
      <h1 className="text-2xl font-bold mb-2">{t('seats.title')}</h1>
      <DepartureHero
        departure={vm.departure}
        fromStation={vm.fromStation}
        toStation={vm.toStation}
      />
      {vm.topError && <div className="text-red-600 mb-4">{vm.topError}</div>}
      <SeatsList
        cars={vm.cars}
        openCars={vm.openCars}
        onToggleCar={vm.toggleCar}
        selected={vm.selected}
        onToggleSeat={vm.toggleSeat}
      />
      <PassengerDetailsSection
        fields={vm.fields}
        seatPriceByKey={vm.seatPriceByKey}
        form={vm.form}
      />
      <SeatsActionBar
        total={vm.total}
        canBook={vm.canBook}
        isSubmitting={vm.isSubmitting}
      />
    </form>
  );
}
