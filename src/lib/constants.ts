export const MAX_BYTES = 10 * 1024 * 1024
export const ALLOWED_SIZES = [16, 24, 32, 48, 64, 128, 256] as const
export const DEFAULT_SIZES: readonly number[] = [16, 32, 48, 64]

/** Rastergröße für SVG und Text (Server arbeitet mit max. 512 px, Reserve für Schärfe). */
export const RASTER_SIZE = 1024
/** Wie favicon_core.MASKABLE_CONTENT_RATIO: Quadrat in der Safe Zone (Kreis mit 40 % Radius). */
export const MASKABLE_CONTENT_RATIO = 0.8 / Math.SQRT2

export const FONT_FALLBACK =
  'system-ui, -apple-system, "Segoe UI", Roboto, "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji", sans-serif'

export const REQUEST_TIMEOUT_MS = 60_000
export const SNIPPET_TIMEOUT_MS = 10_000
