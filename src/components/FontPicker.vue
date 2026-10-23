<script setup lang="ts">
  // Schriftauswahl als Listbox (WAI-ARIA): ein natives <select> kann Einträge nicht zuverlässig
  // in ihrer eigenen Schrift zeigen. Schriften laden erst, wenn ihr Eintrag sichtbar wird.
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { fontCss, fontWeight } from '@/lib/fonts'
  import { useFaviconStore } from '@/stores/favicon'

  interface Option {
    value: string
    label: string
  }

  const PAGE_STEP = 8

  const { t } = useI18n()
  const store = useFaviconStore()

  const root = ref<HTMLElement | null>(null)
  const btn = ref<HTMLButtonElement | null>(null)
  const list = ref<HTMLUListElement | null>(null)
  const open = ref(false)
  const activeIndex = ref(0)

  const options = computed<Option[]>(() => [
    { value: '', label: t('fontSystem') },
    ...store.fontList.map((font, i) => ({ value: String(i), label: font.label })),
  ])
  const currentLabel = computed(
    () => options.value.find((o) => o.value === store.fontValue)?.label ?? t('fontSystem')
  )
  const activeId = computed(() => {
    const opt = options.value[activeIndex.value]
    return open.value && opt ? optionId(opt.value) : undefined
  })

  function optionId(value: string): string {
    return value === '' ? 'textFontOpt-sys' : 'textFontOpt-' + value
  }

  function styleFor(value: string) {
    return { fontFamily: fontCss(value), fontWeight: fontWeight(value) }
  }

  function optionElements(): HTMLElement[] {
    return list.value ? [...list.value.querySelectorAll<HTMLElement>('[role="option"]')] : []
  }

  function setActive(index: number, scroll = true): void {
    const last = options.value.length - 1
    activeIndex.value = Math.max(0, Math.min(last, index))
    if (scroll) optionElements()[activeIndex.value]?.scrollIntoView?.({ block: 'nearest' })
  }

  async function openList(): Promise<void> {
    open.value = true
    await nextTick()
    setActive(
      Math.max(
        0,
        options.value.findIndex((o) => o.value === store.fontValue)
      )
    )
    list.value?.focus()
  }

  function closeList(returnFocus = true): void {
    if (!open.value) return
    open.value = false
    if (returnFocus) btn.value?.focus()
  }

  function choose(index: number): void {
    const opt = options.value[index]
    activeIndex.value = index
    closeList()
    if (opt && opt.value !== store.fontValue) void store.selectFont(opt.value)
  }

  function toggle(): void {
    if (open.value) closeList()
    else void openList()
  }

  function onButtonKeydown(e: KeyboardEvent): void {
    if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key)) {
      e.preventDefault()
      void openList()
    }
  }

  /** Tippen springt zum nächsten Eintrag mit diesem Anfangsbuchstaben. */
  function jumpTo(char: string): void {
    const key = char.toLowerCase()
    const count = options.value.length
    for (let step = 1; step <= count; step++) {
      const i = (activeIndex.value + step) % count
      if (options.value[i]?.label.trim().toLowerCase().startsWith(key)) {
        setActive(i)
        return
      }
    }
  }

  function onListKeydown(e: KeyboardEvent): void {
    switch (e.key) {
      case 'ArrowDown':
        setActive(activeIndex.value + 1)
        break
      case 'ArrowUp':
        setActive(activeIndex.value - 1)
        break
      case 'Home':
        setActive(0)
        break
      case 'End':
        setActive(options.value.length - 1)
        break
      case 'PageDown':
        setActive(activeIndex.value + PAGE_STEP)
        break
      case 'PageUp':
        setActive(activeIndex.value - PAGE_STEP)
        break
      case 'Enter':
      case ' ':
        choose(activeIndex.value)
        break
      case 'Escape':
        closeList()
        break
      case 'Tab':
        closeList(false)
        return
      default:
        if (e.key.length !== 1 || e.ctrlKey || e.metaKey || e.altKey) return
        jumpTo(e.key)
    }
    e.preventDefault()
  }

  function onDocumentPointerDown(e: PointerEvent): void {
    if (open.value && !root.value?.contains(e.target as Node)) closeList(false)
  }

  // Schriften erst laden, wenn ihr Eintrag in der geöffneten Liste sichtbar wird
  let observer: IntersectionObserver | null = null
  function observeOptions(): void {
    if (!observer) return
    observer.disconnect()
    for (const el of optionElements()) {
      if (el.dataset.value) observer.observe(el)
    }
  }

  watch(
    () => store.fontList,
    async () => {
      await nextTick()
      observeOptions()
    }
  )

  onMounted(() => {
    if ('IntersectionObserver' in window && list.value) {
      observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (!entry.isIntersecting) continue
            const el = entry.target as HTMLElement
            observer?.unobserve(el)
            void store.preloadFont(el.dataset.value ?? '')
          }
        },
        { root: list.value, rootMargin: '200px 0px' }
      )
      observeOptions()
    }
    document.addEventListener('pointerdown', onDocumentPointerDown)
  })

  onBeforeUnmount(() => {
    observer?.disconnect()
    document.removeEventListener('pointerdown', onDocumentPointerDown)
  })
</script>

<template>
  <div ref="root" class="font-picker">
    <button
      id="textFontBtn"
      ref="btn"
      type="button"
      class="font-picker-btn"
      aria-haspopup="listbox"
      :aria-expanded="open ? 'true' : 'false'"
      aria-controls="textFontList"
      aria-labelledby="textFontLabel textFontValue"
      @click="toggle"
      @keydown="onButtonKeydown"
    >
      <span id="textFontValue" class="font-picker-value" :style="styleFor(store.fontValue)">
        {{ currentLabel }}
      </span>
    </button>
    <ul
      v-show="open"
      id="textFontList"
      ref="list"
      class="font-picker-list"
      role="listbox"
      tabindex="-1"
      aria-labelledby="textFontLabel"
      :aria-activedescendant="activeId"
      @keydown="onListKeydown"
    >
      <li
        v-for="(opt, i) in options"
        :id="optionId(opt.value)"
        :key="opt.value"
        role="option"
        :data-value="opt.value"
        :aria-selected="opt.value === store.fontValue ? 'true' : 'false'"
        :class="{ active: i === activeIndex }"
        :style="styleFor(opt.value)"
        @click="choose(i)"
        @mousemove="activeIndex = i"
      >
        {{ opt.label }}
      </li>
    </ul>
  </div>
</template>

<style scoped>
  .font-picker {
    position: relative;
    min-width: 0;
  }
  .font-picker-btn {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--ds-space-2);
    width: 100%;
    min-height: 0;
    padding: var(--ds-space-2) var(--ds-space-3);
    border-radius: var(--ds-radius-sm);
    border: var(--ds-border-width) solid var(--ds-border-strong);
    background: var(--ds-surface-1);
    color: var(--ds-text);
    font-size: var(--ds-text-md);
    font-weight: var(--ds-weight-regular);
    text-align: left;
    cursor: pointer;
  }
  /* Globale App-Button-Stile (Akzentfläche, Hover) hier nicht übernehmen */
  .font-picker-btn:hover,
  .font-picker-btn[aria-expanded='true'] {
    background: var(--ds-surface-1);
    border-color: var(--ds-accent);
  }
  .font-picker-btn::after {
    content: '';
    flex: none;
    border: 0.3em solid transparent;
    border-top-color: currentColor;
    border-bottom: 0;
  }
  .font-picker-btn:focus-visible,
  .font-picker-list:focus-visible {
    outline: none;
    box-shadow: var(--ds-focus-ring);
  }
  .font-picker-value {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .font-picker-list {
    position: absolute;
    z-index: 10;
    top: calc(100% + var(--ds-space-1));
    left: 0;
    width: max(100%, 16rem);
    max-height: 20rem;
    overflow-y: auto;
    margin: 0;
    padding: var(--ds-space-1);
    list-style: none;
    border-radius: var(--ds-radius-sm);
    border: var(--ds-border-width) solid var(--ds-border-strong);
    background: var(--ds-surface-1);
    box-shadow: var(--ds-shadow-overlay);
  }
  .font-picker-list li {
    padding: var(--ds-space-2) var(--ds-space-3);
    border-radius: var(--ds-radius-sm);
    font-size: var(--ds-text-lg);
    line-height: 1.3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    cursor: pointer;
  }
  .font-picker-list li.active {
    background: var(--ds-surface-2);
  }
  .font-picker-list li[aria-selected='true'] {
    background: var(--ds-accent-soft);
  }
</style>
