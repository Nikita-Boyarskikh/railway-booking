import { Link, Outlet, useNavigation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Layout } from './Layout';
import LanguageSwitcher from '@features/switch-language/ui/LanguageSwitcher';

export default function RootLayout() {
  const { t } = useTranslation();
  const navigation = useNavigation();
  const isLoading = navigation.state !== 'idle';
  return (
    <>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-white focus:text-blue-700 focus:px-3 focus:py-2 focus:rounded focus:shadow"
      >
        {t('a11y.skipToContent')}
      </a>
      <Layout header={(
        <div className="flex items-center justify-between">
          <Link to="/" className="text-xl font-semibold">{t('app.title')}</Link>
          <LanguageSwitcher />
        </div>
      )}>
        <div
          role="progressbar"
          aria-label={t('a11y.loading')}
          aria-hidden={!isLoading}
          className={`fixed top-0 left-0 h-0.5 bg-blue-400 transition-[width,opacity] duration-300 ${
            isLoading ? 'w-full opacity-100' : 'w-0 opacity-0'
          }`}
        />
        <Outlet />
      </Layout>
    </>
  );
}
