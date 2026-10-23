import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const SRC = join(__dirname, '..')

function read(rel: string): string {
  return readFileSync(join(SRC, rel), 'utf8')
}

/** Selektoren aller Regeln (auch in @media), Leerraum normalisiert, an Kommas getrennt. */
function selectors(css: string): string[] {
  const plain = css.replace(/\/\*[\s\S]*?\*\//g, '')
  return [...plain.matchAll(/(?:^|[{}])\s*([^{}@\s][^{}]*)\{/g)].flatMap((m) =>
    m[1]!
      .replace(/\s+/g, ' ')
      .split(',')
      .map((part) => part.trim())
  )
}

/** Alle <style>-Blöcke der Komponenten plus die globalen CSS-Dateien. */
function allStyles(): Array<[string, string]> {
  const css: Array<[string, string]> = ['styles/base.css', 'styles/controls.css'].map((f) => [
    f,
    read(f),
  ])
  for (const dir of ['', 'components']) {
    for (const file of readdirSync(join(SRC, dir)).filter((f) => f.endsWith('.vue'))) {
      const sfc = read(join(dir, file))
      for (const m of sfc.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)) css.push([file, m[1] ?? ''])
    }
  }
  return css
}

describe('Styles', () => {
  it('Farben nur über Design-Tokens (keine Hex-Werte)', () => {
    for (const [file, css] of allStyles()) {
      expect(css, file).not.toMatch(/#[0-9a-fA-F]{3,8}\b/)
    }
  })

  it('App-Stile schlagen nicht in die SSI-Partials durch', () => {
    // Jeder Selektor in controls.css ist auf #app begrenzt
    const controls = selectors(read('styles/controls.css'))
    expect(controls.length).toBeGreaterThan(10)
    for (const sel of controls) expect(sel).toMatch(/^:where\(#app\)/)
    // base.css kennt keine ungebundenen Element-Regeln für Buttons, färbt aber den Footer-Button wie Links
    const base = read('styles/base.css')
    for (const sel of selectors(base)) expect(sel).not.toMatch(/^button\b/)
    expect(base).toContain("button.footer-link:not([class*='cookie'])")
  })

  it('Dateiauswahl bleibt per Tastatur erreichbar', () => {
    const dropzone = read('components/ImageDropzone.vue')
    expect(dropzone).toContain('clip-path: inset(50%)')
    expect(dropzone).not.toMatch(/input\[type='file'\]\s*\{\s*display:\s*none/)
  })
})
