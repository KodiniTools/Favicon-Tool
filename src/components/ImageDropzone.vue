<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { useFaviconStore } from '@/stores/favicon'

  const ACCEPT = 'image/png,image/jpeg,image/webp,image/gif,image/bmp,image/svg+xml,.svg'

  const { t } = useI18n()
  const store = useFaviconStore()
  const dragover = ref(false)
  const label = computed(() => store.file?.name ?? t('dropzone'))

  function onChange(e: Event): void {
    const input = e.target as HTMLInputElement
    void store.selectFile(input.files?.[0] ?? null)
  }

  function onDrop(e: DragEvent): void {
    dragover.value = false
    const dropped = e.dataTransfer?.files[0]
    if (dropped) void store.selectFile(dropped)
  }
</script>

<template>
  <label
    id="dropzone"
    class="dropzone"
    :class="{ dragover }"
    @dragenter.prevent="dragover = true"
    @dragover.prevent="dragover = true"
    @dragleave.prevent="dragover = false"
    @drop.prevent="onDrop"
  >
    <svg class="dropzone-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M12 16V4m0 0-4.5 4.5M12 4l4.5 4.5M4 15v3.5A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5V15"
      />
    </svg>
    <span id="label-text">{{ label }}</span>
    <span class="dropzone-hint">{{ t('dropzoneHint') }}</span>
    <input id="fileInput" type="file" name="file" :accept="ACCEPT" @change="onChange" />
  </label>
</template>

<style scoped>
  .dropzone {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--ds-space-2);
    min-height: clamp(11rem, 30vw, 15rem);
    border: 2px dashed var(--ds-border-strong);
    border-radius: var(--ds-radius-lg);
    padding: var(--ds-space-6) var(--ds-space-4);
    text-align: center;
    overflow-wrap: anywhere;
    cursor: pointer;
    color: var(--ds-text-2);
    background: var(--ds-surface-0);
    transition:
      border-color var(--ds-duration) var(--ds-ease),
      background-color var(--ds-duration) var(--ds-ease);
  }
  .dropzone:hover,
  .dropzone.dragover {
    border-color: var(--ds-accent);
    background: var(--ds-accent-soft);
    color: var(--ds-text);
  }
  .dropzone-icon {
    width: 2.75rem;
    height: 2.75rem;
    fill: none;
    stroke: var(--ds-accent);
    stroke-width: 1.6;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  #label-text {
    color: var(--ds-text);
    font-size: var(--ds-text-lg);
  }
  .dropzone-hint {
    font-size: var(--ds-text-sm);
    color: var(--ds-text-2);
  }
  .dropzone:focus-within {
    box-shadow: var(--ds-focus-ring);
  }
  /* Visuell versteckt, aber per Tastatur fokussierbar und für Screenreader erreichbar
     (display: none würde die Dateiauswahl aus der Tab-Reihenfolge entfernen) */
  input[type='file'] {
    position: absolute;
    width: 1px;
    height: 1px;
    margin: -1px;
    padding: 0;
    overflow: hidden;
    clip: rect(0 0 0 0);
    clip-path: inset(50%);
    white-space: nowrap;
    border: 0;
  }
</style>
