<script setup lang="ts">
  import { computed } from 'vue'
  import { useI18n } from 'vue-i18n'
  import type { StatusTone } from '@/lib/types'
  import { useFaviconStore } from '@/stores/favicon'

  const TONE_COLORS: Record<StatusTone, string> = {
    info: 'var(--ds-info)',
    success: 'var(--ds-success)',
    warning: 'var(--ds-warning)',
    danger: 'var(--ds-danger)',
  }

  const { t } = useI18n()
  const store = useFaviconStore()
  // Schlüssel werden bei jedem Sprachwechsel neu übersetzt; Servertexte bleiben, wie sie kamen
  const text = computed(() => {
    const s = store.status
    if (!s) return ''
    return s.text ?? (s.key ? t(s.key, s.vars ?? {}) : '')
  })
  const color = computed(() => (store.status ? TONE_COLORS[store.status.tone] : undefined))
</script>

<template>
  <div id="status" role="status" aria-live="polite" :style="{ color }">{{ text }}</div>
</template>

<style scoped>
  #status {
    margin-top: var(--ds-space-4);
    font-size: var(--ds-text-md);
    font-weight: var(--ds-weight-medium);
    min-height: 1.5em;
  }
</style>
