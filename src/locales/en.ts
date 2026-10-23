import type de from './de'

// Texte der Seite (Englisch); gleiche Schlüssel wie de.ts (vom Typ erzwungen)
const en: Record<keyof typeof de, string> = {
  pageTitle: "Favicon Generator – Create favicon.ico & favicon package {'|'} KodiniTools",
  title: 'Favicon Converter',
  intro:
    'Upload an image (PNG, JPG, WebP, GIF, BMP, SVG – max. 10 MB) or enter text/emoji. You get a favicon as ICO, PNG, WebP, GIF, BMP or SVG, or a complete favicon package.',
  modeLabel: 'Source',
  modeImage: 'Image',
  modeText: 'Text / emoji',
  textLabel: 'Text or emoji',
  textPlaceholder: 'e.g. K or 🚀',
  textColorLabel: 'Text color',
  fontLabel: 'Font',
  fontSystem: 'System font (bold)',
  fontLoadFailed: 'Could not load the font – using the system font.',
  noText: 'Please enter text or an emoji.',
  mockTabLight: 'Browser tab light',
  mockTabDark: 'Browser tab dark',
  tabTitleDefault: 'My Website',
  dropzone: 'Choose a file or drag it here',
  fitLegend: 'Non-square images',
  fitPad: 'Pad with transparency',
  fitCrop: 'Crop to center',
  formatLegend: 'Output format',
  formatHint: 'Several sizes are delivered as a ZIP.',
  formatHintGif:
    'GIF only knows fully transparent or opaque pixels; soft edges become hard. Several sizes come as a ZIP.',
  formatHintBmp:
    'BMP has no transparency: transparent areas are filled white or with the background color. Several sizes come as a ZIP.',
  formatHintSvg:
    'SVG is scalable and always a single file. An uploaded SVG stays a vector graphic without styling; otherwise the image is embedded.',
  sizesLegend: 'Sizes (px)',
  styleLegend: 'Appearance',
  bgLabel: 'Background color',
  paddingLabel: 'Padding',
  radiusLabel: 'Corner radius',
  packageLegend: 'Package options (ZIP only)',
  appNameLabel: 'App name for site.webmanifest (optional)',
  themeLabel: 'Theme color',
  snippetSummary: 'HTML code for the {tag}',
  copy: 'Copy',
  copied: 'Copied!',
  copyFailed: 'Copying not possible – please select the text manually.',
  snippetError: 'Could not load the HTML code.',
  appNamePlaceholder: 'e.g. My Website',
  btnPackage: 'Complete package (ZIP)',
  previewFailed: 'Preview not available – the file may not be a valid image.',
  tooLarge: 'File too large (max. 10 MB).',
  noFile: 'Please choose a file first.',
  processing: 'Processing...',
  done: 'Done! Download started.',
  timeout: 'Request timed out – please try again.',
  noSize: 'Select at least one size.',
  httpError: 'Conversion failed (HTTP {status})',
}

export default en
