import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './en.json';
import fr from './fr.json';
import nl from './nl.json';
import ar from './ar.json';

export function initTranslator() {
  return i18n
    .use(initReactI18next)
    .init({
      resources: {
        en: { translation: en },
        fr: { translation: fr },
        nl: { translation: nl },
        ar: { translation: ar },
      },
      lng: 'en', // Default language
      fallbackLng: 'en',
      debug: import.meta.env.DEV,
      interpolation: {
        escapeValue: false,
      },
    });
}

export default i18n;