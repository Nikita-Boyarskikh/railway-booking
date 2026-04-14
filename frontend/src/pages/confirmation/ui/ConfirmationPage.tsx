import type { LoaderFunctionArgs } from 'react-router-dom';
import { useLoaderData } from 'react-router-dom';
import { apiClient } from '@shared/api/client';
import ConfirmationView from '@widgets/confirmation-view/ui/ConfirmationView';

export async function orderLoader({ params }: LoaderFunctionArgs) {
  const id = params['id'];
  if (!id) throw new Response('Missing id', { status: 400 });
  return { order: await apiClient.getOrder(id) };
}

export default function ConfirmationPage() {
  const { order } = useLoaderData<typeof orderLoader>();
  return <ConfirmationView order={order} />;
}
