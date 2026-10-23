// Texte der globalen SSI-Navigation (Schlüssel = data-i18n in nav.html),
// Kopie aus Collage Maker src/stores/settings.ts.
import type { Locale } from '@/i18n'

export const NAV_MESSAGES: Record<Locale, Record<string, string>> = {
  de: {
    'nav.audioTools': 'Audiotools',
    'nav.mp3Converter': 'MP3 Konverter',
    'nav.audioEqualizer': 'Interaktiver Audio Equalizer',
    'nav.modernPlayer': 'Moderner Musikplayer',
    'nav.ultimatePlayer': 'Ultimativer Musikplayer',
    'nav.playlistGenerator': 'Wiedergabeliste Generator',
    'nav.playlistConverter': 'Wiedergabeliste Konverter',
    'nav.alarmTool': 'Alarmtool',
    'nav.audioNormalizer': 'Audio Normalizer',
    'nav.visualizer': 'Visualizer',
    'nav.equalizer19': '19-Band Equalizer',
    'nav.audioConverter': 'Audio Konverter',
    'nav.imageTools': 'Bildtools',
    'nav.imageConverter': 'Bildkonverter',
    'nav.batchImageEditor': 'Bildserie bearbeiten',
    'nav.photoCollage': 'Fotocollage',
    'nav.tools': 'Tools',
    'nav.colorExtractor': 'Kodini Farbextraktor',
    'nav.videoConverter': 'Videokonverter',
    'nav.contact': 'Kontakt',
    'aria.toggleTheme': 'Theme wechseln',
    'aria.selectLanguage': 'Sprache wählen',
    'aria.menuOpen': 'Menü öffnen',
    'aria.menuClose': 'Menü schliessen',
    'aria.mainNav': 'Hauptnavigation',
  },
  en: {
    'nav.audioTools': 'Audio Tools',
    'nav.mp3Converter': 'MP3 Converter',
    'nav.audioEqualizer': 'Interactive Audio Equalizer',
    'nav.modernPlayer': 'Modern Music Player',
    'nav.ultimatePlayer': 'Ultimate Music Player',
    'nav.playlistGenerator': 'Audio Playlist Generator',
    'nav.playlistConverter': 'Playlist to WebM Converter',
    'nav.alarmTool': 'Alarm Tool',
    'nav.audioNormalizer': 'Audio Normalizer',
    'nav.visualizer': 'Visualizer',
    'nav.equalizer19': '19-Band Equalizer',
    'nav.audioConverter': 'Audio Converter',
    'nav.imageTools': 'Image Tools',
    'nav.imageConverter': 'Image Converter',
    'nav.batchImageEditor': 'Batch Image Editor',
    'nav.photoCollage': 'Photo Collage',
    'nav.tools': 'Tools',
    'nav.colorExtractor': 'Kodini Color Extractor',
    'nav.videoConverter': 'Video Converter',
    'nav.contact': 'Contact',
    'aria.toggleTheme': 'Toggle theme',
    'aria.selectLanguage': 'Select language',
    'aria.menuOpen': 'Open menu',
    'aria.menuClose': 'Close menu',
    'aria.mainNav': 'Main navigation',
  },
}

/** Texte der SSI-Navigation (.global-nav) übersetzen und den aktiven Sprachknopf markieren. */
export function translateNav(locale: Locale, root: ParentNode = document): void {
  const nav = root.querySelector('.global-nav')
  if (!nav) return
  const msgs = NAV_MESSAGES[locale]
  nav.querySelectorAll('[data-i18n]').forEach((el) => {
    const text = msgs[el.getAttribute('data-i18n') ?? '']
    if (text) el.textContent = text
  })
  nav.querySelectorAll('[data-i18n-aria]').forEach((el) => {
    const text = msgs[el.getAttribute('data-i18n-aria') ?? '']
    if (text) el.setAttribute('aria-label', text)
  })
  nav.querySelectorAll('[data-i18n-title]').forEach((el) => {
    const text = msgs[el.getAttribute('data-i18n-title') ?? '']
    if (text) el.setAttribute('title', text)
  })
  root.querySelectorAll('.global-nav-lang-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.getAttribute('data-lang') === locale)
  })
}
