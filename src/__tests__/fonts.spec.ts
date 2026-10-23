import { afterEach, describe, expect, it, vi } from 'vitest'
import { createFontLoader, fontCss, fontWeight, isFontEntry } from '@/lib/fonts'

const font = { label: 'Supreme Bold', url: 'static/fonts/Supreme-Bold.woff2', format: 'woff2' }

function mockFontFace(fail = false) {
  const load = vi.fn(() => (fail ? Promise.reject(new Error('kaputt')) : Promise.resolve('face')))
  const FontFaceMock = vi.fn(function (this: { load: typeof load }) {
    this.load = load
  })
  const add = vi.fn()
  vi.stubGlobal('FontFace', FontFaceMock)
  Object.defineProperty(document, 'fonts', { value: { add }, configurable: true })
  return { FontFaceMock, load, add }
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('fonts', () => {
  it('CSS für System- und eigene Schrift', () => {
    expect(fontCss('')).toMatch(/^system-ui/)
    expect(fontCss('2')).toMatch(/^"favicon-font-2", system-ui/)
    expect(fontWeight('')).toBe(700)
    expect(fontWeight('2')).toBe(400)
  })

  it('prüft Einträge aus GET fonts', () => {
    expect(isFontEntry(font)).toBe(true)
    expect(isFontEntry({ label: 'x' })).toBe(false)
    expect(isFontEntry(null)).toBe(false)
  })

  it('lädt jede Schrift nur einmal, auch bei parallelen Aufrufen', async () => {
    const { FontFaceMock, add } = mockFontFace()
    const ensure = createFontLoader()
    const [a, b] = await Promise.all([ensure('0', font), ensure('0', font)])
    expect(a).toBe('favicon-font-0')
    expect(b).toBe('favicon-font-0')
    expect(FontFaceMock).toHaveBeenCalledTimes(1)
    expect(FontFaceMock).toHaveBeenCalledWith(
      'favicon-font-0',
      'url("static/fonts/Supreme-Bold.woff2") format("woff2")'
    )
    expect(add).toHaveBeenCalledTimes(1)
  })

  it('liefert null bei Ladefehler und für die Systemschrift', async () => {
    mockFontFace(true)
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    const ensure = createFontLoader()
    expect(await ensure('1', font)).toBeNull()
    expect(await ensure('', font)).toBeNull()
    expect(await ensure('5', undefined)).toBeNull()
  })
})
