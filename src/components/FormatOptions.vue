<script setup lang="ts">
  import { useI18n } from 'vue-i18n'
  import type { OutputFormat } from '@/lib/types'
  import { useFaviconStore } from '@/stores/favicon'

  const { t } = useI18n()
  const store = useFaviconStore()

  const FORMATS: { value: OutputFormat; label: string }[] = [
    { value: 'ico', label: 'ICO' },
    { value: 'png', label: 'PNG' },
    { value: 'webp', label: 'WebP' },
  ]
</script>

<template>
  <fieldset>
    <legend>{{ t('formatLegend') }}</legend>
    <div id="formatOptions" class="options">
      <label v-for="f in FORMATS" :key="f.value">
        <input v-model="store.format" type="radio" name="format" :value="f.value" />
        <span>{{ f.label }}</span>
      </label>
    </div>
    <p v-if="store.format !== 'ico'" class="hint">{{ t('formatHint') }}</p>
  </fieldset>
</template>

<style scoped>
  .hint {
    margin: var(--ds-space-2) 0 0;
    font-size: var(--ds-text-sm);
    color: var(--ds-text-3);
  }
</style>
