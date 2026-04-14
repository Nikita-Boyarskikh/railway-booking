import i18n from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';
import ru from './locales/ru.json';
import {DEFAULT_LOCALE} from "@shared/config";

export const defaultNS = 'translation';
export const resources = {
  en: { translation: en },
  ru: { translation: ru },
} as const;

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: DEFAULT_LOCALE,
    supportedLngs: ['en', 'ru'],
    defaultNS,
    interpolation: { escapeValue: false },
  });

export default i18n;
