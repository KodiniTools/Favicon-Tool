// Verbindung zu den SSI-Partials (Navigation, Footer, Cookie-Banner) außerhalb von #app:
// Theme-Wechsel übernehmen und Sprache in beide Richtungen synchronisieren.
import { onBeforeUnmount, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { isLocale, type Locale } from '@/i18n'
import { translateNav } from '@/lib/nav'

function storageSet(key: string, value: string): void {
  try {
    localStorage.setItem(key, value)
  } catch {
    // Storage gesperrt
  }
}

/** Theme der Navigation (html[data-theme]) übernehmen: body.light-theme für Token-Parität, Auswahl merken. */
function syncTheme(): void {
  const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'
  document.body.classList.toggle('light-theme', theme === 'light')
  storageSet('theme', theme)
}

export function useGlobalChrome() {
  const { locale, t } = useI18n()

  function applyLocale(next: Locale): void {
    document.documentElement.setAttribute('lang', next)
    document.title = t('pageTitle')
    translateNav(next)
  }

  /** Sprache wechseln (Navigation, anderer Tab); unbekannte Werte werden ignoriert. */
  function setLocale(next: unknown): void {
    if (!isLocale(next)) return
    storageSet('locale', next)
    // Ein vorhandenes ?lang= mitführen, sonst würde es beim Neuladen die Auswahl überschreiben
    const url = new URL(location.href)
    if (url.searchParams.has('lang')) {
      url.searchParams.set('lang', next)
      history.replaceState(history.state, '', url)
    }
    locale.value = next
  }

  const onLocaleChanged = (e: Event) =>
    setLocale((e as CustomEvent<{ locale?: string }>).detail?.locale)
  // Fallback, falls die Navigation das Event nicht selbst auslöst
  const onDocumentClick = (e: MouseEvent) => {
    const target = e.target as Element | null
    const btn = target?.closest?.('.global-nav-lang-btn[data-lang]')
    if (btn) setLocale(btn.getAttribute('data-lang'))
  }
  // Sprachwechsel in einem anderen Tab übernehmen
  const onStorage = (e: StorageEvent) => {
    if (e.key === 'locale' && e.newValue) setLocale(e.newValue)
  }
  const themeObserver = new MutationObserver(syncTheme)

  watch(locale, (next) => applyLocale(next as Locale))

  onMounted(() => {
    syncTheme()
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    })
    window.addEventListener('locale-changed', onLocaleChanged)
    document.addEventListener('click', onDocumentClick)
    window.addEventListener('storage', onStorage)
    applyLocale(locale.value as Locale)
  })

  onBeforeUnmount(() => {
    themeObserver.disconnect()
    window.removeEventListener('locale-changed', onLocaleChanged)
    document.removeEventListener('click', onDocumentClick)
    window.removeEventListener('storage', onStorage)
  })

  return { setLocale }
}
