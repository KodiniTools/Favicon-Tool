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

it('übernimmt eine Auswahl aus einem anderen Tab, ohne sie zurückzuschreiben', async () => {
  const media = Object.assign(new EventTarget(), { matches: true })
  vi.stubGlobal('matchMedia', () => media)

  try {
    document.body.innerHTML = `
      <label hidden>
        <select>
          <option value="auto">System</option>
          <option value="light">Hell</option>
          <option value="dark">Dunkel</option>
        </select>
      </label>
    `
    const select = document.querySelector('select')!
    const root = document.documentElement
    localStorage.clear()
    root.dataset.theme = 'light'
    connectToolTheme(select)
    expect(select.value).toBe('light')

    // Anderer Tab wählt „System“ (OS dunkel): schreibt erst den Modus, dann den Theme-Wert
    const setItem = vi.spyOn(Storage.prototype, 'setItem')
    const removeItem = vi.spyOn(Storage.prototype, 'removeItem')
    localStorage.setItem('favicon-theme-mode', 'auto')
    localStorage.setItem('theme', 'dark')
    setItem.mockClear()
    window.dispatchEvent(
      new StorageEvent('storage', { key: 'favicon-theme-mode', newValue: 'auto' })
    )
    window.dispatchEvent(new StorageEvent('storage', { key: 'theme', newValue: 'dark' }))
    await Promise.resolve()

    expect(select.value).toBe('auto')
    expect(root.dataset.theme).toBe('dark')
    expect(setItem).not.toHaveBeenCalled()
    expect(removeItem).not.toHaveBeenCalled()
    expect(localStorage.getItem('favicon-theme-mode')).toBe('auto')
    setItem.mockRestore()
    removeItem.mockRestore()
  } finally {
    vi.unstubAllGlobals()
  }
})
