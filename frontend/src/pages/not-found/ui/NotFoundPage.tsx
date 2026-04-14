import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export default function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <div className="text-center py-16">
      <title>{t('notFound.pageTitle')}</title>
      <h1 className="text-5xl font-bold text-gray-800 mb-2">{t('notFound.title')}</h1>
      <p className="text-gray-600 mb-6">{t('notFound.message')}</p>
      <Link to="/" className="text-blue-600 hover:underline">{t('common.backToSearch')}</Link>
    </div>
  );
}
