// Eigene Schriften aus static/fonts (GET fonts): einmal laden, dann im Dokument verfügbar.
import { FONT_FALLBACK } from './constants'
import type { FontEntry } from './types'

/** CSS-Familienname für die Schrift mit Index `value` ('' = Systemschrift). */
export function fontFamilyName(value: string): string {
  return 'favicon-font-' + value
}

/** CSS font-family für Auswahl, Eingabefeld und Listeneintrag. */
export function fontCss(value: string): string {
  return value === '' ? FONT_FALLBACK : `"${fontFamilyName(value)}", ${FONT_FALLBACK}`
}

export function fontWeight(value: string): number {
  return value === '' ? 700 : 400
}

export function isFontEntry(value: unknown): value is FontEntry {
  if (!value || typeof value !== 'object') return false
  const v = value as Record<string, unknown>
  return typeof v.label === 'string' && typeof v.url === 'string' && typeof v.format === 'string'
}

/**
 * Lädt Schriften genau einmal (auch bei parallelen Aufrufen).
 * Ergebnis: Familienname oder null bei Fehler.
 */
export function createFontLoader() {
  const loads = new Map<string, Promise<string | null>>()
  return function ensureFont(value: string, font: FontEntry | undefined): Promise<string | null> {
    if (value === '' || !font) return Promise.resolve(null)
    let load = loads.get(value)
    if (!load) {
      const family = fontFamilyName(value)
      load = (async () => {
        try {
          const face = new FontFace(family, `url("${font.url}") format("${font.format}")`)
          document.fonts.add(await face.load())
          return family
        } catch (err) {
          console.warn('Schrift konnte nicht geladen werden:', font.url, err)
          return null
        }
      })()
      loads.set(value, load)
    }
    return load
  }
}
