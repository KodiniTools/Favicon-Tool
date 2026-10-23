import { describe, expect, it } from 'vitest'
import { drawSquare, drawStyled, fitTitle, textFont } from '@/lib/draw'
import type { Source } from '@/lib/types'

/** Minimaler Canvas-Kontext, der Aufrufe mitschreibt (jsdom hat kein Canvas). */
function fakeCtx(textWidth = 10) {
  const calls: Array<[string, unknown[]]> = []
  const record =
    (name: string) =>
    (...args: unknown[]) => {
      calls.push([name, args])
    }
  const ctx = {
    calls,
    fillStyle: '',
    imageSmoothingQuality: 'low',
    save: record('save'),
    restore: record('restore'),
    translate: record('translate'),
    beginPath: record('beginPath'),
    roundRect: record('roundRect'),
    clip: record('clip'),
    fillRect: record('fillRect'),
    drawImage: record('drawImage'),
    measureText: (text: string) => ({ width: text.length * textWidth }),
  }
  return ctx as unknown as CanvasRenderingContext2D & { calls: typeof calls }
}

const wide: Source = { img: {} as CanvasImageSource, w: 200, h: 100 }

describe('drawSquare', () => {
  it('füllt nicht-quadratische Bilder transparent auf (pad)', () => {
    const ctx = fakeCtx()
    drawSquare(ctx, wide, 'pad', 0, 0, 64)
    expect(ctx.calls).toEqual([['drawImage', [wide.img, 0, 16, 64, 32]]])
  })

  it('schneidet mittig zu (crop)', () => {
    const ctx = fakeCtx()
    drawSquare(ctx, wide, 'crop', 0, 0, 64)
    expect(ctx.calls).toEqual([['drawImage', [wide.img, 50, 0, 100, 100, 0, 0, 64, 64]]])
  })
})

describe('drawStyled', () => {
  it('ohne Gestaltung: kein Clip, kein Hintergrund', () => {
    const ctx = fakeCtx()
    drawStyled(ctx, wide, 'pad', { background: '', padding: 0, radius: 0 }, 0, 0, 64)
    const names = ctx.calls.map(([name]) => name)
    expect(names).not.toContain('clip')
    expect(names).not.toContain('fillRect')
  })

  it('Radius, Hintergrund und Innenabstand wie favicon_core.apply_style', () => {
    const ctx = fakeCtx()
    drawStyled(ctx, wide, 'crop', { background: '#ff0000', padding: 25, radius: 50 }, 0, 0, 64)
    expect(ctx.calls.find(([n]) => n === 'roundRect')?.[1]).toEqual([0, 0, 64, 64, 16])
    expect(ctx.calls.find(([n]) => n === 'fillRect')?.[1]).toEqual([0, 0, 64, 64])
    // 25 % je Seite -> Motiv 32 px, zentriert bei 16
    expect(ctx.calls.find(([n]) => n === 'drawImage')?.[1].slice(5)).toEqual([16, 16, 32, 32])
  })
})

describe('Text', () => {
  it('eigene Schrift normal, Systemschrift fett', () => {
    expect(textFont('favicon-font-3', 100)).toMatch(/^400 100px "favicon-font-3", system-ui/)
    expect(textFont(null, 50)).toMatch(/^700 50px system-ui/)
  })

  it('kürzt zu lange Tab-Titel mit Auslassungszeichen', () => {
    const ctx = fakeCtx(10)
    expect(fitTitle(ctx, 'Kurz', 100)).toBe('Kurz')
    expect(fitTitle(ctx, 'Ein sehr langer Titel', 100)).toBe('Ein sehr …')
  })
})
