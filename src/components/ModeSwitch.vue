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
  /* Segment-Schalter: aktiver Modus als gefüllte Akzentfläche, inaktiver neutral */
  .mode {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--ds-space-1);
    margin-bottom: var(--ds-space-4);
    padding: var(--ds-space-1);
    border: var(--ds-border-width) solid var(--ds-border-strong);
    border-radius: var(--ds-radius-lg);
    background: var(--ds-surface-0);
  }
  .mode label {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--ds-space-2);
    min-height: var(--ds-control-lg);
    border: var(--ds-border-width) solid transparent;
    border-radius: var(--ds-radius-md);
    color: var(--ds-text-2);
    font-size: var(--ds-text-md);
    font-weight: var(--ds-weight-medium);
    cursor: pointer;
    transition:
      background-color var(--ds-duration) var(--ds-ease),
      color var(--ds-duration) var(--ds-ease);
  }
  .mode label:hover {
    color: var(--ds-text);
    background: var(--ds-surface-2);
  }
  .mode label:has(input:checked) {
    border-color: var(--ds-accent);
    background: var(--ds-accent);
    color: var(--ds-on-accent);
    box-shadow: var(--ds-shadow-overlay);
  }
  .mode input {
    accent-color: var(--ds-on-accent);
  }
  .mode label:focus-within {
    box-shadow: var(--ds-focus-ring);
  }
</style>
