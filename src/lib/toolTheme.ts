type Theme = 'light' | 'dark'
type ThemeMode = Theme | 'auto'

const MODE_KEY = 'favicon-theme-mode'
const THEME_KEY = 'theme'

function readSetting(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function saveSetting(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {
    // Die Auswahl bleibt für die aktuelle Seite wirksam.
  }
}

export function connectToolTheme(select: HTMLSelectElement | null): void {
  const root = document.documentElement
  const system = window.matchMedia?.('(prefers-color-scheme: dark)')
  const currentTheme = (): Theme => (root.dataset.theme === 'dark' ? 'dark' : 'light')
  let mode: ThemeMode = readSetting(MODE_KEY) === 'auto' ? 'auto' : currentTheme()
  let applied: Theme = currentTheme()

  function apply(next: ThemeMode): void {
    mode = next
    applied = mode === 'auto' ? (system?.matches ? 'dark' : 'light') : mode
    root.dataset.theme = applied
    document.body.classList.toggle('light-theme', applied === 'light')
    if (select) select.value = mode
    // Die globale Navigation nutzt den aufgelösten Hell-/Dunkelwert.
    saveSetting(THEME_KEY, applied)
    saveSetting(MODE_KEY, mode === 'auto' ? 'auto' : null)
  }

  apply(mode)
  select?.closest('label')?.removeAttribute('hidden')
  select?.addEventListener('change', () => {
    if (select.value === 'auto' || select.value === 'light' || select.value === 'dark') {
      apply(select.value)
    }
  })
  system?.addEventListener('change', () => {
    if (mode === 'auto') apply('auto')
  })

  new MutationObserver(() => {
    if (currentTheme() !== applied) apply(currentTheme())
  }).observe(root, { attributeFilter: ['data-theme'] })

  window.addEventListener('storage', (event) => {
    if (event.key !== THEME_KEY && event.key !== MODE_KEY) return
    const saved = readSetting(THEME_KEY)
    if (readSetting(MODE_KEY) === 'auto') apply('auto')
    else if (saved === 'light' || saved === 'dark') apply(saved)
  })
}
