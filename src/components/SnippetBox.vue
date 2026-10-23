<script setup lang="ts">
  // HTML-Snippet (Quelle: GET snippet, identisch mit favicon-snippet.html im Paket)
  import { ref, watch } from 'vue'
  import { useI18n } from 'vue-i18n'
  import type { MessageKey } from '@/i18n'
  import { errorDetail, fetchWithTimeout } from '@/lib/api'
  import { SNIPPET_TIMEOUT_MS } from '@/lib/constants'
  import { useFaviconStore } from '@/stores/favicon'

  const { t, locale } = useI18n()
  // als Variable, weil ein Literal '<head>' im Template den HTML-Parser stört
  const HEAD_TAG = '<head>'
  const store = useFaviconStore()
  const code = ref<HTMLElement | null>(null)
  const snippet = ref('')
  const snippetFailed = ref(false)
  const copyStatus = ref<MessageKey | null>(null)

  let request = 0
  async function loadSnippet(): Promise<void> {
    const current = ++request
    const params = new URLSearchParams({ lang: String(locale.value) })
    if (store.hasSvg) params.set('svg', 'true')
    if (store.themeEnabled) params.set('theme_color', store.themeColor)
    try {
      const res = await fetchWithTimeout('snippet?' + params.toString(), {}, SNIPPET_TIMEOUT_MS)
      if (!res.ok) throw new Error(await errorDetail(res, 'HTTP ' + res.status))
      const text = await res.text()
      if (current === request) {
        snippet.value = text
        snippetFailed.value = false
      }
    } catch (err) {
      console.warn('Snippet konnte nicht geladen werden:', err)
      if (current === request) snippetFailed.value = true
    }
  }

  async function copySnippet(): Promise<void> {
    let ok = false
    try {
      await navigator.clipboard.writeText(snippet.value)
      ok = true
    } catch {
      // Fallback ohne Clipboard-API (z. B. ohne HTTPS): Text markieren und kopieren
      const selection = window.getSelection()
      if (code.value && selection) {
        const range = document.createRange()
        range.selectNodeContents(code.value)
        selection.removeAllRanges()
        selection.addRange(range)
        try {
          ok = document.execCommand('copy')
        } catch {
          ok = false
        }
      }
    }
    copyStatus.value = ok ? 'copied' : 'copyFailed'
  }

  watch(
    () => [store.hasSvg, store.themeEnabled, store.themeColor] as const,
    () => void loadSnippet(),
    { immediate: true }
  )
  watch(locale, () => {
    copyStatus.value = null
  })
</script>

<template>
  <details id="snippetBox" class="snippet">
    <summary>{{ t('snippetSummary', { tag: HEAD_TAG }) }}</summary>
    <pre><code id="snippet" ref="code">{{ snippetFailed ? t('snippetError') : snippet }}</code></pre>
    <div class="copy-row">
      <button id="btnCopy" type="button" class="secondary" @click="copySnippet">
        {{ t('copy') }}
      </button>
      <span id="copyStatus" role="status" aria-live="polite">{{
        copyStatus ? t(copyStatus) : ''
      }}</span>
    </div>
  </details>
</template>

<style scoped>
  .snippet {
    margin-top: var(--ds-space-5);
    text-align: left;
  }
  .snippet summary {
    cursor: pointer;
    font-size: var(--ds-text-sm);
    font-weight: var(--ds-weight-medium);
    color: var(--ds-text-2);
  }
  .snippet pre {
    margin: var(--ds-space-3) 0;
    padding: var(--ds-space-3);
    overflow-x: auto;
    background: var(--ds-surface-0);
    border: var(--ds-border-width) solid var(--ds-border);
    border-radius: var(--ds-radius-sm);
    font-size: var(--ds-text-xs);
    line-height: 1.5;
  }
  .copy-row {
    display: flex;
    align-items: center;
    gap: var(--ds-space-3);
  }
  .copy-row button {
    flex: 0 0 auto;
    min-height: var(--ds-control-md);
    padding: var(--ds-space-2) var(--ds-space-4);
    font-size: var(--ds-text-md);
  }
  #copyStatus {
    font-size: var(--ds-text-sm);
    color: var(--ds-text-2);
  }
</style>
