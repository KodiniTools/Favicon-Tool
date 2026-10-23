import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from '@/App.vue'
import { createAppI18n } from '@/i18n'
import { useFaviconStore } from '@/stores/favicon'

const FONTS = [
  { label: 'Alpino Black', url: 'static/fonts/Alpino-Black.woff2', format: 'woff2' },
  { label: 'Chillax Bold', url: 'static/fonts/Chillax-Bold.woff2', format: 'woff2' },
]

function stubFetch() {
  const fetchMock = vi.fn(async (url: string) => {
    if (url === 'fonts') return new Response(JSON.stringify(FONTS))
    if (url.startsWith('snippet')) return new Response('<link rel="icon" href="/favicon.ico">')
    return new Response('', { status: 404 })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

function stubFontFace() {
  vi.stubGlobal(
    'FontFace',
    vi.fn(function (this: { load: () => Promise<string> }) {
      this.load = () => Promise.resolve('face')
    })
  )
  Object.defineProperty(document, 'fonts', { value: { add: vi.fn() }, configurable: true })
}

async function mountApp(locale: 'de' | 'en' = 'de') {
  const pinia = createPinia()
  const wrapper = mount(App, {
    attachTo: document.body,
    global: { plugins: [pinia, createAppI18n(locale)] },
  })
  await flushPromises()
  return { wrapper, store: useFaviconStore(pinia) }
}

beforeEach(() => {
  document.body.innerHTML = ''
  document.documentElement.setAttribute('lang', 'de')
  localStorage.clear()
  stubFetch()
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('App', () => {
  it('zeigt Titel, Upload für Bilder und SVG und die Snippet-Vorschau', async () => {
    const { wrapper } = await mountApp()
    expect(wrapper.find('h1').text()).toBe('Favicon Konverter')
    expect(wrapper.find('p').text()).toContain('ICO, PNG, WebP, GIF, BMP oder SVG')
    expect(wrapper.find('#fileInput').attributes('accept')).toContain('image/svg+xml')
    expect(wrapper.find('#label-text').text()).toBe('Datei auswählen oder hierher ziehen')
    expect(wrapper.find('#snippet').text()).toContain('rel="icon"')
    expect(wrapper.find('summary').text()).toBe('HTML-Code für den <head>')
    wrapper.unmount()
  })

  it('Ausgabeformat wählbar: Knopf und Hinweis passen sich an', async () => {
    const { wrapper, store } = await mountApp()
    const labels = wrapper.findAll('#formatOptions label').map((l) => l.text())
    expect(labels).toEqual(['ICO', 'PNG', 'WebP', 'GIF', 'BMP', 'SVG'])
    expect(wrapper.find('#btnIco').text()).toBe('favicon.ico')
    expect(wrapper.text()).not.toContain('als ZIP geliefert')
    await wrapper.find('input[name="format"][value="png"]').setValue(true)
    expect(store.format).toBe('png')
    expect(wrapper.find('#btnIco').text()).toBe('favicon.png')
    expect(wrapper.text()).toContain('Mehrere Größen werden als ZIP geliefert.')
    await wrapper.find('input[name="format"][value="svg"]').setValue(true)
    expect(wrapper.find('#btnIco').text()).toBe('favicon.svg')
    expect(wrapper.text()).toContain('SVG ist skalierbar und immer eine Datei.')
    await wrapper.find('input[name="format"][value="bmp"]').setValue(true)
    expect(wrapper.text()).toContain('BMP hat keine Transparenz')
    wrapper.unmount()
  })

  it('Größen sind bei ICO und SVG gesperrt; das Paket nennt seine festen Formate', async () => {
    const { wrapper } = await mountApp()
    const sizeSet = () => wrapper.find('#sizeOptions').element.closest('fieldset')!
    expect(sizeSet().disabled).toBe(true)
    const checked = wrapper
      .findAll<HTMLInputElement>('#sizeOptions input')
      .filter((i) => i.element.checked)
      .map((i) => i.element.value)
    expect(checked).toEqual(['16', '32', '48', '64'])
    expect(wrapper.find('#sizesHint').text()).toContain('Standardgrößen 16, 32, 48 und 64')
    await wrapper.find('input[name="format"][value="png"]').setValue(true)
    expect(sizeSet().disabled).toBe(false)
    expect(wrapper.find('#sizesHint').exists()).toBe(false)
    await wrapper.find('input[name="format"][value="svg"]').setValue(true)
    expect(sizeSet().disabled).toBe(true)
    // Format und Größen liegen im Bereich der Einzeldatei, nicht beim Paket
    const single = wrapper.find('section[aria-labelledby="singleHeading"]')
    expect(single.find('#formatOptions').exists()).toBe(true)
    expect(single.find('#btnIco').exists()).toBe(true)
    const pkg = wrapper.find('section[aria-labelledby="packageHeading"]')
    expect(pkg.find('#formatOptions').exists()).toBe(false)
    expect(pkg.find('#packageContents').text()).toContain('gilt nur für die einzelne Datei')
    expect(pkg.find('#btnPkg').text()).toBe('Paket herunterladen (ZIP)')
    wrapper.unmount()
  })

  it('Textmodus blendet Upload aus und Textfelder ein', async () => {
    const { wrapper } = await mountApp()
    expect(wrapper.find('#textPanel').isVisible()).toBe(false)
    await wrapper.find('input[name="mode"][value="text"]').setValue(true)
    expect(wrapper.find('#textPanel').isVisible()).toBe(true)
    expect(wrapper.find('#dropzone').isVisible()).toBe(false)
    for (const id of ['mkTabLight', 'mkTabDark', 'mkIos', 'mkAndroid']) {
      expect(wrapper.find('#' + id).exists()).toBe(true)
    }
    wrapper.unmount()
  })

  it('übernimmt den Sprachwechsel der Navigation inklusive Seitentitel und Statusmeldung', async () => {
    const { wrapper, store } = await mountApp()
    store.setStatusKey('noFile', 'danger')
    await flushPromises()
    expect(wrapper.find('#status').text()).toBe('Bitte zuerst eine Datei auswählen.')
    expect(document.title).toBe(
      'Favicon Generator – favicon.ico & Favicon-Paket erstellen | KodiniTools'
    )

    window.dispatchEvent(new CustomEvent('locale-changed', { detail: { locale: 'en' } }))
    await flushPromises()
    expect(wrapper.find('h1').text()).toBe('Favicon Converter')
    expect(wrapper.find('#status').text()).toBe('Please choose a file first.')
    expect(document.documentElement.getAttribute('lang')).toBe('en')
    expect(document.title).toBe(
      'Favicon Generator – Create favicon.ico & favicon package | KodiniTools'
    )
    expect(localStorage.getItem('locale')).toBe('en')

    // Unbekannte Sprache wird ignoriert
    window.dispatchEvent(new CustomEvent('locale-changed', { detail: { locale: 'fr' } }))
    await flushPromises()
    expect(wrapper.find('h1').text()).toBe('Favicon Converter')
    wrapper.unmount()
  })

  it('übersetzt die SSI-Navigation und markiert den aktiven Sprachknopf', async () => {
    document.body.innerHTML = `
      <nav class="global-nav"><a data-i18n="nav.imageTools">Bildtools</a>
        <button class="global-nav-lang-btn" data-lang="de">DE</button>
        <button class="global-nav-lang-btn" data-lang="en">EN</button></nav>`
    const { wrapper } = await mountApp()
    ;(document.querySelector('[data-lang="en"]') as HTMLButtonElement).click()
    await flushPromises()
    expect(document.querySelector('[data-i18n="nav.imageTools"]')?.textContent).toBe('Image Tools')
    expect(document.querySelector('[data-lang="en"]')?.classList.contains('active')).toBe(true)
    wrapper.unmount()
  })
})

describe('Schriftauswahl', () => {
  it('listet die Schriften jeweils in ihrer eigenen Schrift', async () => {
    const { wrapper } = await mountApp()
    const options = wrapper.findAll('#textFontList [role="option"]')
    expect(options.map((o) => o.text())).toEqual([
      'Systemschrift (fett)',
      'Alpino Black',
      'Chillax Bold',
    ])
    expect(options[1]!.attributes('style')).toContain('favicon-font-0')
    expect(options[0]!.attributes('aria-selected')).toBe('true')
    wrapper.unmount()
  })

  it('Tastatur: öffnen, Anfangsbuchstabe, Enter wählt; Fokus zurück auf den Knopf', async () => {
    stubFontFace()
    const { wrapper, store } = await mountApp()
    await wrapper.find('input[name="mode"][value="text"]').setValue(true)
    const btn = wrapper.find('#textFontBtn')
    await btn.trigger('keydown', { key: 'ArrowDown' })
    await flushPromises()
    const list = wrapper.find('#textFontList')
    expect(btn.attributes('aria-expanded')).toBe('true')
    expect(list.isVisible()).toBe(true)
    expect(document.activeElement?.id).toBe('textFontList')

    await list.trigger('keydown', { key: 'c' })
    expect(list.attributes('aria-activedescendant')).toBe('textFontOpt-1')
    await list.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(store.fontValue).toBe('1')
    expect(wrapper.find('#textFontValue').text()).toBe('Chillax Bold')
    expect(wrapper.find('#iconText').attributes('style')).toContain('favicon-font-1')
    expect(list.isVisible()).toBe(false)
    expect(document.activeElement?.id).toBe('textFontBtn')

    // Home + Enter: zurück zur Systemschrift
    await btn.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    await list.trigger('keydown', { key: 'Home' })
    await list.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(store.fontValue).toBe('')
    wrapper.unmount()
  })

  it('Escape und Klick außerhalb schließen die Liste', async () => {
    const { wrapper } = await mountApp()
    await wrapper.find('input[name="mode"][value="text"]').setValue(true)
    const btn = wrapper.find('#textFontBtn')
    const list = wrapper.find('#textFontList')
    await btn.trigger('click')
    await flushPromises()
    expect(list.isVisible()).toBe(true)
    await flushPromises()
    await list.trigger('keydown', { key: 'Escape' })
    expect(list.isVisible()).toBe(false)

    await btn.trigger('click')
    await flushPromises()
    document.body.dispatchEvent(new Event('pointerdown', { bubbles: true }))
    await flushPromises()
    expect(list.isVisible()).toBe(false)
    wrapper.unmount()
  })
})
