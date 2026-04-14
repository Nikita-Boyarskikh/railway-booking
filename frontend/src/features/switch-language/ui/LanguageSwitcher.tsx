import { useTranslation } from 'react-i18next';
import {LANGUAGES} from "@shared/config";

export default function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const current = i18n.resolvedLanguage ?? i18n.language;
  return (
    <select
      className="bg-blue-700 text-white border border-blue-500 rounded px-2 py-1 text-sm"
      value={current}
      onChange={(e) => { void i18n.changeLanguage(e.target.value); }}
      aria-label={t('a11y.languageSwitcher')}
    >
      {LANGUAGES.map((l) => (
        <option key={l.code} value={l.code}>{l.label}</option>
      ))}
    </select>
  );
}
