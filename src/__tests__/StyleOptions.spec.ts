import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { describe, expect, it } from 'vitest'
import StyleOptions from '@/components/StyleOptions.vue'
import { createAppI18n } from '@/i18n'
import { useFaviconStore } from '@/stores/favicon'

function mountOptions(locale: 'de' | 'en' = 'de') {
  const pinia = createPinia()
  const wrapper = mount(StyleOptions, { global: { plugins: [pinia, createAppI18n(locale)] } })
  return { wrapper, store: useFaviconStore(pinia) }
}

describe('StyleOptions: Schieberegler mit Zahlenfeld und Zurücksetzen', () => {
  it('Zahlenfeld, Regler und Store bleiben synchron', async () => {
    const { wrapper, store } = mountOptions()
    await wrapper.get('#paddingNum').setValue('12')
    expect(store.padding).toBe(12)
    expect((wrapper.get('#padding').element as HTMLInputElement).value).toBe('12')

    await wrapper.get('#radius').setValue('30')
    expect(store.radius).toBe(30)
    expect((wrapper.get('#radiusNum').element as HTMLInputElement).value).toBe('30')
  })

  it('begrenzt auf den Serverbereich und stellt ungültige Eingaben wieder her', async () => {
    const { wrapper, store } = mountOptions()
    const num = wrapper.get('#paddingNum')
    await num.setValue('99')
    expect(store.padding).toBe(40)
    await num.setValue('-5')
    expect(store.padding).toBe(0)
    await num.setValue('7')
    // Leeres Feld ändert den Wert nicht; beim Verlassen erscheint wieder der gültige Wert
    ;(num.element as HTMLInputElement).value = ''
    await num.trigger('input')
    expect(store.padding).toBe(7)
    await num.trigger('change')
    expect((num.element as HTMLInputElement).value).toBe('7')
    await wrapper.get('#radiusNum').setValue('80')
    expect(store.radius).toBe(50)
  })

  it('Zurücksetzen setzt nur den eigenen Regler auf 0', async () => {
    const { wrapper, store } = mountOptions('en')
    store.padding = 20
    store.radius = 25
    await wrapper.vm.$nextTick()
    const btn = wrapper.get('#paddingReset')
    expect(btn.attributes('aria-label')).toBe('Reset Padding')
    expect(btn.text()).toContain('Reset')
    await btn.trigger('click')
    expect(store.padding).toBe(0)
    expect(store.radius).toBe(25)
    await wrapper.get('#radiusReset').trigger('click')
    expect(store.radius).toBe(0)
  })
})
