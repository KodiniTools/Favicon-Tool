export type Mode = 'image' | 'text'
export type Fit = 'pad' | 'crop'
export type StatusTone = 'info' | 'success' | 'warning' | 'danger'

/** Gestaltung wie auf dem Server (favicon_core.apply_style). */
export interface IconStyle {
  /** CSS-Farbe oder '' für transparent */
  background: string
  /** Innenabstand in Prozent je Seite (0–40) */
  padding: number
  /** Eckenradius in Prozent der halben Kantenlänge (0–50) */
  radius: number
}

/** Zeichenbare Quelle mit ihrer natürlichen Größe. */
export interface Source {
  img: CanvasImageSource
  w: number
  h: number
}

/** Eintrag aus GET fonts (static/fonts). */
export interface FontEntry {
  label: string
  url: string
  format: string
}
