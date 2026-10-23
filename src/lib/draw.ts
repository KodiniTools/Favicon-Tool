// Zeichenfunktionen für Vorschau und Upload; Geometrie wie auf dem Server (favicon_core).
import { FONT_FALLBACK, MASKABLE_CONTENT_RATIO } from './constants'
import type { Fit, IconStyle, Source } from './types'

export interface TextOptions {
  text: string
  color: string
  /** CSS-Familienname einer geladenen eigenen Schrift, sonst null (Systemschrift fett) */
  family: string | null
}

export function roundedRectPath(ctx: CanvasRenderingContext2D, size: number, r: number): void {
  ctx.beginPath()
  if (typeof ctx.roundRect === 'function') {
    ctx.roundRect(0, 0, size, size, r)
    return
  }
  ctx.moveTo(r, 0)
  ctx.arcTo(size, 0, size, size, r)
  ctx.arcTo(size, size, 0, size, r)
  ctx.arcTo(0, size, 0, 0, r)
  ctx.arcTo(0, 0, size, 0, r)
  ctx.closePath()
}

/** CSS-Schriftangabe für Text-Icons: eigene Schrift normal, Systemschrift fett. */
export function textFont(family: string | null, px: number): string {
  // Eigene Schrift: Schnitt steckt in der Datei, daher normales Gewicht (kein künstliches Fett)
  return family ? `400 ${px}px "${family}", ${FONT_FALLBACK}` : `700 ${px}px ${FONT_FALLBACK}`
}

/** Text/Emoji möglichst groß und optisch zentriert auf eine transparente Fläche zeichnen. */
export function renderTextCanvas(size: number, options: TextOptions): HTMLCanvasElement | null {
  const text = options.text.trim()
  if (!text) return null
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = size
  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  ctx.fillStyle = options.color
  ctx.textAlign = 'left'
  ctx.textBaseline = 'alphabetic'
  let fontSize = size
  ctx.font = textFont(options.family, fontSize)
  let m = ctx.measureText(text)
  const boxW = m.actualBoundingBoxLeft + m.actualBoundingBoxRight
  const boxH = m.actualBoundingBoxAscent + m.actualBoundingBoxDescent
  fontSize *= Math.min((size * 0.86) / Math.max(boxW, 1), (size * 0.86) / Math.max(boxH, 1))
  ctx.font = textFont(options.family, fontSize)
  m = ctx.measureText(text)
  const x =
    (size - (m.actualBoundingBoxLeft + m.actualBoundingBoxRight)) / 2 + m.actualBoundingBoxLeft
  const y =
    (size - (m.actualBoundingBoxAscent + m.actualBoundingBoxDescent)) / 2 +
    m.actualBoundingBoxAscent
  ctx.fillText(text, x, y)
  return canvas
}

/** Quelle quadratisch (pad/crop) in ein Feld (x, y, size) zeichnen – ohne Gestaltung. */
export function drawSquare(
  ctx: CanvasRenderingContext2D,
  src: Source,
  fit: Fit,
  x: number,
  y: number,
  size: number
): void {
  if (fit === 'crop') {
    const side = Math.min(src.w, src.h)
    ctx.drawImage(src.img, (src.w - side) / 2, (src.h - side) / 2, side, side, x, y, size, size)
  } else {
    const scale = size / Math.max(src.w, src.h)
    const dw = src.w * scale
    const dh = src.h * scale
    ctx.drawImage(src.img, x + (size - dw) / 2, y + (size - dh) / 2, dw, dh)
  }
}

/** Icon mit Gestaltung wie auf dem Server (favicon_core.apply_style) an Position (x, y). */
export function drawStyled(
  ctx: CanvasRenderingContext2D,
  src: Source,
  fit: Fit,
  style: IconStyle,
  x: number,
  y: number,
  size: number
): void {
  ctx.save()
  ctx.translate(x, y)
  ctx.imageSmoothingQuality = 'high'
  if (style.radius) {
    roundedRectPath(ctx, size, (size / 2) * (style.radius / 100))
    ctx.clip()
  }
  if (style.background) {
    ctx.fillStyle = style.background
    ctx.fillRect(0, 0, size, size)
  }
  const inner = Math.max(1, (size * (100 - 2 * style.padding)) / 100)
  drawSquare(ctx, src, fit, (size - inner) / 2, (size - inner) / 2, inner)
  ctx.restore()
}

// Farben der Browser-Tab-Attrappe (Chrome hell/dunkel); bewusst fest, unabhängig vom Seiten-Theme
export const TAB_THEMES = {
  light: { strip: '#dee1e6', tab: '#ffffff', text: '#1f1f1f' },
  dark: { strip: '#202124', tab: '#35363a', text: '#e8eaed' },
} as const

/** Längsten Titel ermitteln, der in maxWidth passt (sonst mit „…“ gekürzt). */
export function fitTitle(ctx: CanvasRenderingContext2D, title: string, maxWidth: number): string {
  let shown = title
  while (shown.length > 1 && ctx.measureText(shown + '…').width > maxWidth)
    shown = shown.slice(0, -1)
  return shown === title ? title : shown + '…'
}

export function drawTab(
  canvas: HTMLCanvasElement,
  theme: keyof typeof TAB_THEMES,
  src: Source,
  fit: Fit,
  style: IconStyle,
  title: string
): void {
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const c = TAB_THEMES[theme]
  const w = canvas.width
  const h = canvas.height
  ctx.clearRect(0, 0, w, h)
  ctx.fillStyle = c.strip
  ctx.fillRect(0, 0, w, h)
  ctx.fillStyle = c.tab
  ctx.beginPath()
  ctx.moveTo(6, h)
  ctx.arcTo(6, 6, 18, 6, 8)
  ctx.arcTo(w - 6, 6, w - 6, h, 8)
  ctx.lineTo(w - 6, h)
  ctx.closePath()
  ctx.fill()
  drawStyled(ctx, src, fit, style, 18, 15, 16)
  ctx.fillStyle = c.text
  ctx.font = '12px system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
  ctx.textBaseline = 'middle'
  ctx.fillText(fitTitle(ctx, title, w - 60), 42, 23)
}

export function drawHomeIcon(
  canvas: HTMLCanvasElement,
  src: Source,
  fit: Fit,
  style: IconStyle,
  platform: 'ios' | 'android'
): void {
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const size = canvas.width
  ctx.clearRect(0, 0, size, size)
  ctx.save()
  ctx.beginPath()
  if (platform === 'ios') {
    // iOS rundet selbst ab; Server liefert deckend mit Innenabstand, ohne Radius
    roundedRectPath(ctx, size, size * 0.225)
  } else {
    // Android maskiert z. B. kreisförmig; maskable Icon mit Motiv in der Safe Zone
    ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2)
  }
  ctx.clip()
  ctx.fillStyle = style.background || '#ffffff'
  ctx.fillRect(0, 0, size, size)
  if (platform === 'ios') {
    drawStyled(ctx, src, fit, { background: '', padding: style.padding, radius: 0 }, 0, 0, size)
  } else {
    const inner = size * MASKABLE_CONTENT_RATIO
    drawSquare(ctx, src, fit, (size - inner) / 2, (size - inner) / 2, inner)
  }
  ctx.restore()
}

/** Quelle auf ein Raster mit längster Kante `size` bringen (SVG → PNG für den Upload). */
export function rasterize(src: Source, size: number): HTMLCanvasElement | null {
  const scale = size / Math.max(src.w, src.h)
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(src.w * scale))
  canvas.height = Math.max(1, Math.round(src.h * scale))
  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  ctx.drawImage(src.img, 0, 0, canvas.width, canvas.height)
  return canvas
}

export function canvasToPng(canvas: HTMLCanvasElement): Promise<Blob | null> {
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))
}
