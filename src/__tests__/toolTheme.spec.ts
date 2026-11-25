import { expect, it, vi } from 'vitest'
import { connectToolTheme } from '../lib/toolTheme'

it('synchronises system, local selection and the global navigation theme', async () => {
  const system = new EventTarget()
  const media = Object.assign(system, { matches: false })
  vi.stubGlobal('matchMedia', () => media)

  try {
    document.body.innerHTML = `
      <label hidden>
        Design
        <select>
          <option value="auto">System</option>
          <option value="light">Hell</option>
          <option value="dark">Dunkel</option>
        </select>
      </label>
    `
    const select = document.querySelector('select')!
    const root = document.documentElement
    localStorage.setItem('favicon-theme-mode', 'auto')
    connectToolTheme(select)
    expect(select.value).toBe('auto')
    expect(root.dataset.theme).toBe('light')
    expect(select.closest('label')?.hidden).toBe(false)

    media.matches = true
    media.dispatchEvent(new Event('change'))
    expect(root.dataset.theme).toBe('dark')
    expect(localStorage.getItem('theme')).toBe('dark')

    root.dataset.theme = 'light'
    await Promise.resolve()
    expect(select.value).toBe('light')
    expect(localStorage.getItem('favicon-theme-mode')).toBeNull()
    expect(document.body.classList.contains('light-theme')).toBe(true)

    select.value = 'dark'
    select.dispatchEvent(new Event('change'))
    expect(root.dataset.theme).toBe('dark')
    expect(localStorage.getItem('theme')).toBe('dark')
  } finally {
    vi.unstubAllGlobals()
  }
})
