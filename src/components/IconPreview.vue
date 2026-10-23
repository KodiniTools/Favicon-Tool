<script setup lang="ts">
  // Vorschau (64/32/16 px) und Einsatz-Attrappen, gezeichnet wie auf dem Server
  import { ref, watchEffect } from 'vue'
  import { useI18n } from 'vue-i18n'
  import { drawHomeIcon, drawStyled, drawTab } from '@/lib/draw'
  import { useFaviconStore } from '@/stores/favicon'

  const PREVIEW_SIZES = [64, 32, 16] as const

  const { t } = useI18n()
  const store = useFaviconStore()
  const visible = ref(false)
  const previews = ref<HTMLCanvasElement[]>([])
  const tabLight = ref<HTMLCanvasElement | null>(null)
  const tabDark = ref<HTMLCanvasElement | null>(null)
  const ios = ref<HTMLCanvasElement | null>(null)
  const android = ref<HTMLCanvasElement | null>(null)

  watchEffect(
    () => {
      const src = store.source()
      visible.value = src !== null
      if (!src) return
      const { fit, style } = store
      for (const canvas of previews.value) {
        const ctx = canvas.getContext('2d')
        if (!ctx) continue
        ctx.clearRect(0, 0, canvas.width, canvas.height)
        drawStyled(ctx, src, fit, style, 0, 0, canvas.width)
      }
      const title = store.appName.trim() || t('tabTitleDefault')
      if (tabLight.value) drawTab(tabLight.value, 'light', src, fit, style, title)
      if (tabDark.value) drawTab(tabDark.value, 'dark', src, fit, style, title)
      if (ios.value) drawHomeIcon(ios.value, src, fit, style, 'ios')
      if (android.value) drawHomeIcon(android.value, src, fit, style, 'android')
    },
    { flush: 'post' }
  )
</script>

<template>
  <div v-show="visible" id="preview">
    <figure v-for="size in PREVIEW_SIZES" :key="size">
      <canvas :id="'pv' + size" ref="previews" :width="size" :height="size"></canvas>
      <figcaption>{{ size }}</figcaption>
    </figure>
  </div>

  <!-- So sieht das Icon im Einsatz aus (gezeichnet wie auf dem Server) -->
  <div v-show="visible" id="mockups">
    <figure>
      <canvas id="mkTabLight" ref="tabLight" width="220" height="40"></canvas>
      <figcaption>{{ t('mockTabLight') }}</figcaption>
    </figure>
    <figure>
      <canvas id="mkTabDark" ref="tabDark" width="220" height="40"></canvas>
      <figcaption>{{ t('mockTabDark') }}</figcaption>
    </figure>
    <figure>
      <canvas id="mkIos" ref="ios" width="60" height="60"></canvas>
      <figcaption>iOS</figcaption>
    </figure>
    <figure>
      <canvas id="mkAndroid" ref="android" width="60" height="60"></canvas>
      <figcaption>Android</figcaption>
    </figure>
  </div>
</template>

<style scoped>
  #preview,
  #mockups {
    display: flex;
    margin-top: var(--ds-space-5);
    justify-content: center;
    align-items: flex-end;
  }
  #preview {
    gap: var(--ds-space-4);
  }
  #mockups {
    gap: var(--ds-space-4);
    flex-wrap: wrap;
  }
  figure {
    margin: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--ds-space-1);
  }
  figcaption {
    font-size: var(--ds-text-xs);
    color: var(--ds-text-3);
  }
  #mockups canvas {
    border-radius: var(--ds-radius-sm);
  }
  #preview canvas {
    /* Schachbrett zur Darstellung von Transparenz */
    background: repeating-conic-gradient(var(--ds-surface-3) 0% 25%, var(--ds-surface-1) 0% 50%) 0
      0 / 8px 8px;
    image-rendering: pixelated;
    border: var(--ds-border-width) solid var(--ds-border);
    border-radius: 2px;
  }
</style>
