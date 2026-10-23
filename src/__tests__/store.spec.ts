import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MAX_BYTES } from '@/lib/constants'
import { isSvgFile, useFaviconStore } from '@/stores/favicon'

function pngFile(name = 'logo.png', size = 100): File {
  return new File([new Uint8Array(size)], name, { type: 'image/png' })
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  setActivePinia(createPinia())
  // jsdom: kein Objekt-URL-Support, Bilder laden nie
  vi.stubGlobal(
    'URL',
    Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:x'), revokeObjectURL: vi.fn() })
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('Dateiauswahl', () => {
  it('erkennt SVG an Typ oder Endung', () => {
    expect(isSvgFile(new File([''], 'a.svg'))).toBe(true)
    expect(isSvgFile(new File([''], 'a', { type: 'image/svg+xml' }))).toBe(true)
    expect(isSvgFile(pngFile())).toBe(false)
  })

  it('zu große Datei: Hinweis, keine Vorschau', async () => {
    const store = useFaviconStore()
    const big = pngFile('gross.png')
    Object.defineProperty(big, 'size', { value: MAX_BYTES + 1 })
    await store.selectFile(big)
    expect(store.status).toEqual({ key: 'tooLarge', tone: 'danger', vars: undefined })
    expect(store.previewImage).toBeNull()
  })
})

describe('ICO erzeugen', () => {
  it('ohne Größe: Hinweis, keine Anfrage', async () => {
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    const store = useFaviconStore()
    store.sizes = []
    await store.generateIco('de')
    expect(store.status?.key).toBe('noSize')
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('ohne Datei: Hinweis', async () => {
    const store = useFaviconStore()
    await store.generateIco('de')
    expect(store.status?.key).toBe('noFile')
  })

  it('sendet Datei, sortierte Größen, Gestaltung und Sprache und lädt herunter', async () => {
    const fetchMock = vi.fn(async (_url: string, _init: RequestInit) => new Response('ico'))
    vi.stubGlobal('fetch', fetchMock)
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const store = useFaviconStore()
    store.file = pngFile()
    store.sizes = [64, 16, 32]
    store.fit = 'crop'
    store.bgEnabled = true
    store.bgColor = '#112233'
    store.padding = 10
    await store.generateIco('en')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toBe('convert')
    const body = init.body as FormData
    expect(body.get('sizes')).toBe('16,32,64')
    expect(body.get('fit')).toBe('crop')
    expect(body.get('lang')).toBe('en')
    expect(body.get('background')).toBe('#112233')
    expect(body.get('padding')).toBe('10')
    expect(body.get('radius')).toBe('0')
    expect((body.get('file') as File).name).toBe('logo.png')
    expect(store.status).toEqual({ key: 'done', tone: 'success', vars: undefined })
    expect(click).toHaveBeenCalled()
    expect(store.status?.key).toBe('done')
    expect(store.busy).toBe(false)
  })

  it('zeigt die Fehlermeldung des Servers', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse(400, { detail: 'Fehler: kaputt' }))
    )
    const store = useFaviconStore()
    store.file = pngFile()
    await store.generateIco('de')
    expect(store.status).toEqual({ text: 'Fehler: kaputt', tone: 'danger' })
  })

  it('ohne lesbare Fehlermeldung: HTTP-Status', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response('oops', { status: 502 }))
    )
    const store = useFaviconStore()
    store.file = pngFile()
    await store.generateIco('de')
    expect(store.status).toMatchObject({ key: 'httpError', vars: { status: 502 } })
  })

  it('Zeitüberschreitung', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Promise.reject(new DOMException('x', 'AbortError')))
    )
    const store = useFaviconStore()
    store.file = pngFile()
    await store.generateIco('de')
    expect(store.status?.key).toBe('timeout')
    expect(store.busy).toBe(false)
  })
})

describe('Paket erzeugen', () => {
  it('sendet App-Name, Theme-Farbe nur wenn aktiv und kein SVG bei Rasterbild', async () => {
    const fetchMock = vi.fn(async (_url: string, _init: RequestInit) => new Response('zip'))
    vi.stubGlobal('fetch', fetchMock)
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    const store = useFaviconStore()
    store.file = pngFile()
    store.appName = 'Meine App'
    store.themeColor = '#abcdef'
    await store.generatePackage('de')
    let body = fetchMock.mock.calls[0]![1].body as FormData
    expect(fetchMock.mock.calls[0]![0]).toBe('package')
    expect(body.get('app_name')).toBe('Meine App')
    expect(body.get('theme_color')).toBe('')
    expect(body.get('svg')).toBe('')

    store.themeEnabled = true
    await store.generatePackage('de')
    body = fetchMock.mock.calls[1]![1].body as FormData
    expect(body.get('theme_color')).toBe('#abcdef')
  })

  it('Textmodus ohne Text: Hinweis', async () => {
    const store = useFaviconStore()
    store.mode = 'text'
    store.iconText = '   '
    await store.generatePackage('de')
    expect(store.status?.key).toBe('noText')
  })
})

describe('Schriften', () => {
  it('lädt die Liste und verwirft ungültige Einträge', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        jsonResponse(200, [{ label: 'A', url: 'static/fonts/A.woff2', format: 'woff2' }, { x: 1 }])
      )
    )
    const store = useFaviconStore()
    await store.loadFontList()
    expect(store.fontList).toEqual([{ label: 'A', url: 'static/fonts/A.woff2', format: 'woff2' }])
  })

  it('Ladefehler: Hinweis und Rückfall auf die Systemschrift', async () => {
    vi.stubGlobal(
      'FontFace',
      vi.fn(function (this: { load: () => Promise<never> }) {
        this.load = () => Promise.reject(new Error('kaputt'))
      })
    )
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    const store = useFaviconStore()
    store.fontList = [{ label: 'A', url: 'static/fonts/A.woff2', format: 'woff2' }]
    await store.selectFont('0')
    expect(store.fontValue).toBe('')
    expect(store.status?.key).toBe('fontLoadFailed')
  })
})
