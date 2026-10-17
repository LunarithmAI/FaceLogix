import i18n, { type TOptions } from 'i18next';
import { initReactI18next } from 'react-i18next';
import { en } from './en';
import { vi } from './vi';

export const supportedLanguages = ['en', 'vi'] as const;
export type SupportedLanguage = (typeof supportedLanguages)[number];

const STORAGE_KEY = 'facelogix-language';

function isSupportedLanguage(value: string | null): value is SupportedLanguage {
  return value !== null && supportedLanguages.includes(value as SupportedLanguage);
}

function getInitialLanguage(): SupportedLanguage {
  const storedLanguage = window.localStorage.getItem(STORAGE_KEY);
  if (isSupportedLanguage(storedLanguage)) {
    return storedLanguage;
  }
  return window.navigator.language.toLowerCase().startsWith('vi') ? 'vi' : 'en';
}

void i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      vi: { translation: vi },
    },
    lng: getInitialLanguage(),
    fallbackLng: 'en',
    supportedLngs: supportedLanguages,
    load: 'languageOnly',
    keySeparator: false,
    nsSeparator: false,
    interpolation: { escapeValue: false },
    returnNull: false,
    initAsync: false,
  });

export function getCurrentLanguage(): SupportedLanguage {
  return i18n.resolvedLanguage === 'vi' ? 'vi' : 'en';
}

export function translate(key: string, options?: TOptions): string {
  return i18n.t(key, options);
}

export async function changeLanguage(language: SupportedLanguage): Promise<void> {
  window.localStorage.setItem(STORAGE_KEY, language);
  document.documentElement.lang = language;
  await i18n.changeLanguage(language);
}

document.documentElement.lang = getCurrentLanguage();

export default i18n;
