<script setup lang="ts">
  import { useI18n } from 'vue-i18n'
  import { useFaviconStore } from '@/stores/favicon'

  const { t } = useI18n()
  const store = useFaviconStore()
</script>

<template>
  <!-- Quelle: Bild oder Text/Emoji -->
  <div class="mode" role="radiogroup" :aria-label="t('modeLabel')">
    <label>
      <input v-model="store.mode" type="radio" name="mode" value="image" />
      <span>{{ t('modeImage') }}</span>
    </label>
    <label>
      <input v-model="store.mode" type="radio" name="mode" value="text" />
      <span>{{ t('modeText') }}</span>
    </label>
  </div>
</template>

<style scoped>
  .mode {
    display: flex;
    gap: var(--ds-space-2);
    margin-bottom: var(--ds-space-4);
  }
  .mode label {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--ds-space-2);
    min-height: var(--ds-control-md);
    border: var(--ds-border-width) solid var(--ds-border-strong);
    border-radius: var(--ds-radius-md);
    background: var(--ds-surface-2);
    font-size: var(--ds-text-md);
    font-weight: var(--ds-weight-medium);
    cursor: pointer;
  }
  .mode label:has(input:checked) {
    border-color: var(--ds-accent);
    background: var(--ds-accent-soft);
  }
  .mode input {
    accent-color: var(--ds-accent);
  }
  .mode label:focus-within {
    box-shadow: var(--ds-focus-ring);
  }
</style>
