import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import type { Locale, MessageKey } from '@/i18n'
import {
  dispositionFilename,
  downloadBlob,
  errorDetail,
  fetchWithTimeout,
  isAbortError,
} from '@/lib/api'
import { DEFAULT_SIZES, MAX_BYTES, RASTER_SIZE, REQUEST_TIMEOUT_MS } from '@/lib/constants'
import { canvasToPng, rasterize, renderTextCanvas } from '@/lib/draw'
import { createFontLoader, isFontEntry } from '@/lib/fonts'
import type { FontEntry, Fit, IconStyle, Mode, OutputFormat, Source, StatusTone } from '@/lib/types'

/** Statusmeldung: übersetzbarer Schlüssel oder fertiger Text (z. B. Fehlermeldung des Servers). */
export interface Status {
  tone: StatusTone
  key?: MessageKey
  vars?: Record<string, string | number>
  text?: string
}

type UploadError = 'noText' | 'noFile' | 'tooLarge' | 'previewFailed'
type Upload = { blob: Blob; name: string } | { error: UploadError }

export function isSvgFile(file: File): boolean {
  return file.type === 'image/svg+xml' || /\.svg$/i.test(file.name)
}

function loadImage(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve(img)
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Bild konnte nicht geladen werden'))
    }
    img.src = url
  })
}

export const useFaviconStore = defineStore('favicon', () => {
  // --- Quelle ---
  const mode = ref<Mode>('image')
  const file = shallowRef<File | null>(null)
  /** SVG-Quelltext der aktuellen Datei (für favicon.svg im Paket), sonst null */
  const svgText = ref<string | null>(null)
  const previewImage = shallowRef<HTMLImageElement | null>(null)
  const iconText = ref('K')
  const textColor = ref('#1f2937')

  // --- Schriften (static/fonts) ---
  /** Index der gewählten Schrift als String, '' = Systemschrift */
  const fontValue = ref('')
  const fontList = ref<FontEntry[]>([])
  /** Erfolgreich geladene Schriften: Index -> CSS-Familienname */
  const loadedFonts = ref<Record<string, string>>({})
  const ensureFont = createFontLoader()

  // --- Optionen ---
  const fit = ref<Fit>('pad')
  const format = ref<OutputFormat>('ico')
  const sizes = ref<number[]>([...DEFAULT_SIZES])
  const bgEnabled = ref(false)
  const bgColor = ref('#ffffff')
  const padding = ref(0)
  const radius = ref(0)
  const appName = ref('')
  const themeEnabled = ref(false)
  const themeColor = ref('#ffffff')

  // --- Zustand ---
  const status = ref<Status | null>(null)
  const busy = ref(false)

  const style = computed<IconStyle>(() => ({
    background: bgEnabled.value ? bgColor.value : '',
    padding: padding.value,
    radius: radius.value,
  }))
  const hasSvg = computed(() => mode.value === 'image' && svgText.value !== null)
  const fontFamily = computed(() => loadedFonts.value[fontValue.value] ?? null)

  function setStatus(next: Status | null): void {
    status.value = next
  }

  function setStatusKey(key: MessageKey, tone: StatusTone, vars?: Record<string, string | number>) {
    status.value = { key, tone, vars }
  }

  /** Text-Icon als Canvas der Kantenlänge `size`, null ohne Text. */
  function renderText(size: number): HTMLCanvasElement | null {
    return renderTextCanvas(size, {
      text: iconText.value,
      color: textColor.value,
      family: fontFamily.value,
    })
  }

  /** Aktuelle Quelle für Vorschau und Upload (liest reaktive Werte, daher in watchEffect nutzbar). */
  function source(): Source | null {
    if (mode.value === 'text') {
      const canvas = renderText(512)
      return canvas ? { img: canvas, w: canvas.width, h: canvas.height } : null
    }
    const img = previewImage.value
    if (!img) return null
    // SVG ohne width/height liefert im Browser teils 0 als natürliche Größe
    return { img, w: img.naturalWidth || 512, h: img.naturalHeight || 512 }
  }

  let fileToken = 0
  /** Neue Datei übernehmen: Größe prüfen, SVG-Quelltext lesen, Vorschau laden. */
  async function selectFile(next: File | null): Promise<void> {
    const token = ++fileToken
    status.value = null
    file.value = next
    previewImage.value = null
    svgText.value = null
    if (!next) return
    if (next.size > MAX_BYTES) {
      setStatusKey('tooLarge', 'danger')
      return
    }
    if (isSvgFile(next)) {
      try {
        const text = await next.text()
        if (token === fileToken) svgText.value = text
      } catch {
        // SVG-Quelltext nicht lesbar: Upload läuft dann ohne favicon.svg
      }
    }
    try {
      const img = await loadImage(next)
      if (token === fileToken) previewImage.value = img // sonst inzwischen andere Datei gewählt
    } catch {
      if (token === fileToken) setStatusKey('previewFailed', 'warning')
    }
  }

  /** Datei für den Upload: Rasterbilder unverändert, SVG und Text als PNG aus dem Browser. */
  async function uploadBlob(): Promise<Upload> {
    if (mode.value === 'text') {
      const canvas = renderText(RASTER_SIZE)
      if (!canvas) return { error: 'noText' }
      const blob = await canvasToPng(canvas)
      return blob ? { blob, name: 'text.png' } : { error: 'previewFailed' }
    }
    const current = file.value
    if (!current) return { error: 'noFile' }
    if (current.size > MAX_BYTES) return { error: 'tooLarge' }
    if (svgText.value === null) return { blob: current, name: current.name }
    const src = source()
    const canvas = src && rasterize(src, RASTER_SIZE)
    const blob = canvas && (await canvasToPng(canvas))
    if (!blob) return { error: 'previewFailed' }
    return { blob, name: current.name.replace(/\.svg$/i, '') + '.png' }
  }

  function styleFields(): Record<string, string> {
    return {
      background: style.value.background,
      padding: String(style.value.padding),
      radius: String(style.value.radius),
    }
  }

  async function generate(
    endpoint: 'convert' | 'package',
    filename: string,
    fields: Record<string, string>,
    locale: Locale
  ): Promise<void> {
    if (busy.value) return
    const upload = await uploadBlob()
    if ('error' in upload) {
      setStatusKey(upload.error, upload.error === 'previewFailed' ? 'warning' : 'danger')
      return
    }
    const formData = new FormData()
    formData.append('file', upload.blob, upload.name)
    formData.append('fit', fit.value)
    formData.append('lang', locale)
    for (const [k, v] of Object.entries(fields)) formData.append(k, v)

    busy.value = true
    setStatusKey('processing', 'info')
    try {
      // Relativer Aufruf passend zum Subpath
      const res = await fetchWithTimeout(
        endpoint,
        { method: 'POST', body: formData },
        REQUEST_TIMEOUT_MS
      )
      if (!res.ok) {
        const detail = await errorDetail(res, '')
        if (detail) setStatus({ text: detail, tone: 'danger' })
        else setStatusKey('httpError', 'danger', { status: res.status })
        return
      }
      // Dateiname vom Server (PNG/WebP: eine Datei oder ZIP je nach Anzahl der Größen)
      downloadBlob(await res.blob(), dispositionFilename(res, filename))
      setStatusKey('done', 'success')
    } catch (err) {
      if (isAbortError(err)) setStatusKey('timeout', 'danger')
      else setStatus({ text: err instanceof Error ? err.message : String(err), tone: 'danger' })
    } finally {
      busy.value = false
    }
  }

  /** Icons im gewählten Format; die Konvertierung erfolgt auf dem Server (Pillow). */
  function generateIcons(locale: Locale): Promise<void> {
    if (!sizes.value.length) {
      setStatusKey('noSize', 'danger')
      return Promise.resolve()
    }
    const sorted = [...sizes.value].sort((a, b) => a - b)
    return generate(
      'convert',
      format.value === 'ico' ? 'favicon.ico' : `favicon.${format.value}`,
      {
        sizes: sorted.join(','),
        format: format.value,
        // SVG-Ausgabe: Original-SVG mitschicken, damit es als Vektor erhalten bleiben kann
        svg: format.value === 'svg' && hasSvg.value && svgText.value !== null ? svgText.value : '',
        ...styleFields(),
      },
      locale
    )
  }

  function generatePackage(locale: Locale): Promise<void> {
    return generate(
      'package',
      'favicon-package.zip',
      {
        app_name: appName.value,
        theme_color: themeEnabled.value ? themeColor.value : '',
        svg: hasSvg.value && svgText.value !== null ? svgText.value : '',
        ...styleFields(),
      },
      locale
    )
  }

  async function loadFontList(): Promise<void> {
    try {
      const res = await fetch('fonts')
      if (!res.ok) throw new Error('HTTP ' + res.status)
      const data: unknown = await res.json()
      fontList.value = Array.isArray(data) ? data.filter(isFontEntry) : []
    } catch (err) {
      console.warn('Schriftliste nicht verfügbar:', err)
      fontList.value = []
    }
  }

  /** Schrift laden, ohne sie auszuwählen (Listeneinträge in ihrer eigenen Schrift). */
  async function preloadFont(value: string): Promise<string | null> {
    const family = await ensureFont(value, fontList.value[Number(value)])
    if (family && loadedFonts.value[value] !== family) {
      loadedFonts.value = { ...loadedFonts.value, [value]: family }
    }
    return family
  }

  /** Schrift wählen; bei Ladefehler Hinweis und Rückfall auf die Systemschrift. */
  async function selectFont(value: string): Promise<void> {
    fontValue.value = value
    if (value === '') return
    const family = await preloadFont(value)
    if (fontValue.value !== value) return // inzwischen andere Schrift gewählt
    if (!family) {
      setStatusKey('fontLoadFailed', 'warning')
      fontValue.value = ''
    }
  }

  return {
    mode,
    file,
    svgText,
    previewImage,
    iconText,
    textColor,
    fontValue,
    fontList,
    loadedFonts,
    fit,
    format,
    sizes,
    bgEnabled,
    bgColor,
    padding,
    radius,
    appName,
    themeEnabled,
    themeColor,
    status,
    busy,
    style,
    hasSvg,
    fontFamily,
    setStatus,
    setStatusKey,
    source,
    selectFile,
    uploadBlob,
    generateIcons,
    generatePackage,
    loadFontList,
    preloadFont,
    selectFont,
  }
})
