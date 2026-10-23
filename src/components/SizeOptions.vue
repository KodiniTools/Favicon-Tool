<script setup lang="ts">
  import { computed } from 'vue'
  import { useI18n } from 'vue-i18n'
  import type { MessageKey } from '@/i18n'
  import { ALLOWED_SIZES } from '@/lib/constants'
  import { useFaviconStore } from '@/stores/favicon'

  const { t } = useI18n()
  const store = useFaviconStore()

  // Bei ICO und SVG sind die Größen vorgegeben: Kacheln gesperrt, Hinweis warum
  const hint = computed<MessageKey | null>(() => {
    if (store.format === 'ico') return 'sizesHintIco'
    if (store.format === 'svg') return 'sizesHintSvg'
    return null
  })
</script>

<template>
  <fieldset :disabled="store.fixedSizes !== null">
    <legend>{{ t('sizesLegend') }}</legend>
    <div id="sizeOptions" class="options">
      <label v-for="size in ALLOWED_SIZES" :key="size">
        <input
          v-if="store.fixedSizes === null"
          v-model="store.sizes"
          type="checkbox"
          name="size"
          :value="size"
        />
        <input
          v-else
          type="checkbox"
          name="size"
          :value="size"
          :checked="store.fixedSizes.includes(size)"
        />
        {{ size }}
      </label>
    </div>
    <p v-if="hint" id="sizesHint" class="hint">{{ t(hint) }}</p>
  </fieldset>
</template>

<style scoped>
  fieldset:disabled .options {
    opacity: 0.55;
  }
  .hint {
    margin: var(--ds-space-2) 0 0;
    font-size: var(--ds-text-sm);
    color: var(--ds-text-3);
  }
</style>
