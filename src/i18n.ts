import { createI18n } from 'vue-i18n'
import de from './locales/de'
import en from './locales/en'

export type Locale = 'de' | 'en'
export type MessageKey = keyof typeof de

export function isLocale(value: unknown): value is Locale {
  return value === 'de' || value === 'en'
}

/** Startsprache: das Inline-Skript in index.html setzt <html lang> aus ?lang= bzw. localStorage. */
export function initialLocale(): Locale {
  return document.documentElement.getAttribute('lang') === 'en' ? 'en' : 'de'
}

export function createAppI18n(locale: Locale = initialLocale()) {
  return createI18n({
    legacy: false,
    locale,
    fallbackLocale: 'de',
    messages: { de, en },
  })
}
