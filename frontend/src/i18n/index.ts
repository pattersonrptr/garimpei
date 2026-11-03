/**
 * i18n setup (i18next + react-i18next).
 *
 * - Language: the one the user picked (saved in localStorage), otherwise the
 *   browser's, otherwise DEFAULT_LANGUAGE. "en-US" resolves to "en".
 * - Missing keys fall back to DEFAULT_LANGUAGE (pt-BR), the source language.
 *
 * How to add a language: see src/i18n/README.md.
 */

import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'
import {
  DEFAULT_LANGUAGE,
  NAMESPACES,
  resources,
  SUPPORTED_LANGUAGES,
} from './resources'

export const LANGUAGE_STORAGE_KEY = 'garimpei.language'

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    ns: [...NAMESPACES],
    defaultNS: 'common',
    fallbackLng: DEFAULT_LANGUAGE,
    supportedLngs: SUPPORTED_LANGUAGES.map((language) => language.code),
    interpolation: { escapeValue: false }, // React already escapes
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: LANGUAGE_STORAGE_KEY,
      caches: ['localStorage'],
    },
  })

function syncDocumentLanguage(language: string) {
  if (typeof document !== 'undefined') document.documentElement.lang = language
}
syncDocumentLanguage(i18n.resolvedLanguage ?? DEFAULT_LANGUAGE)
i18n.on('languageChanged', syncDocumentLanguage)

/** Active language code (one of SUPPORTED_LANGUAGES). */
export function currentLanguage(): string {
  return i18n.resolvedLanguage ?? DEFAULT_LANGUAGE
}

export { DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES }
export default i18n
