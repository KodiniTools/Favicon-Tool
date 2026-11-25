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
  <section v-show="visible" class="icon-preview" aria-labelledby="icon-preview-title">
    <h2 id="icon-preview-title">{{ t('previewHeading') }}</h2>
    <div class="preview-groups">
      <section class="preview-group" aria-labelledby="preview-sizes-title">
        <h3 id="preview-sizes-title">{{ t('previewSizes') }}</h3>
        <div id="preview">
          <figure v-for="size in PREVIEW_SIZES" :key="size">
            <div class="pixel-frame">
              <canvas :id="'pv' + size" ref="previews" :width="size" :height="size"></canvas>
            </div>
            <figcaption>{{ size }} px</figcaption>
          </figure>
        </div>
      </section>

      <div id="mockups">
        <section class="preview-group" aria-labelledby="preview-tabs-title">
          <h3 id="preview-tabs-title">{{ t('previewTabs') }}</h3>
          <div class="preview-tabs">
            <figure>
              <canvas id="mkTabLight" ref="tabLight" width="220" height="40"></canvas>
              <figcaption>{{ t('mockTabLight') }}</figcaption>
            </figure>
            <figure>
              <canvas id="mkTabDark" ref="tabDark" width="220" height="40"></canvas>
              <figcaption>{{ t('mockTabDark') }}</figcaption>
            </figure>
          </div>
        </section>

        <section class="preview-group" aria-labelledby="preview-home-title">
          <h3 id="preview-home-title">{{ t('previewHome') }}</h3>
          <div class="preview-home">
            <figure>
              <canvas id="mkIos" ref="ios" width="60" height="60"></canvas>
              <figcaption>iOS</figcaption>
            </figure>
            <figure>
              <canvas id="mkAndroid" ref="android" width="60" height="60"></canvas>
              <figcaption>Android</figcaption>
            </figure>
          </div>
        </section>
      </div>
    </div>
  </section>
</template>

<style scoped src="../styles/stage4-preview.css"></style>
