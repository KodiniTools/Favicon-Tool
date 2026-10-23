<script setup lang="ts">
  import { onMounted } from 'vue'
  import { I18nT, useI18n } from 'vue-i18n'
  import FitOptions from '@/components/FitOptions.vue'
  import FormatOptions from '@/components/FormatOptions.vue'
  import IconPreview from '@/components/IconPreview.vue'
  import ImageDropzone from '@/components/ImageDropzone.vue'
  import ModeSwitch from '@/components/ModeSwitch.vue'
  import PackageOptions from '@/components/PackageOptions.vue'
  import SizeOptions from '@/components/SizeOptions.vue'
  import SnippetBox from '@/components/SnippetBox.vue'
  import StatusMessage from '@/components/StatusMessage.vue'
  import StyleOptions from '@/components/StyleOptions.vue'
  import TextPanel from '@/components/TextPanel.vue'
  import { useGlobalChrome } from '@/composables/useGlobalChrome'
  import type { Locale } from '@/i18n'
  import { useFaviconStore } from '@/stores/favicon'

  const { t, locale } = useI18n()
  const store = useFaviconStore()
  useGlobalChrome()

  onMounted(() => {
    void store.loadFontList()
  })

  function createIcons(): void {
    void store.generateIcons(locale.value as Locale)
  }

  function createPackage(): void {
    void store.generatePackage(locale.value as Locale)
  }
</script>

<template>
  <div class="card">
    <h1>{{ t('title') }}</h1>
    <I18nT keypath="intro" tag="p">
      <template #file><code>favicon.ico</code></template>
    </I18nT>

    <form id="uploadForm" @submit.prevent="createIcons">
      <ModeSwitch />
      <ImageDropzone v-show="store.mode === 'image'" />
      <TextPanel v-show="store.mode === 'text'" />
      <IconPreview />
      <FitOptions />
      <FormatOptions />
      <SizeOptions />
      <StyleOptions />
      <PackageOptions />

      <div class="buttons">
        <button id="btnIco" type="submit" :disabled="store.busy">
          {{ store.format === 'ico' ? 'favicon.ico' : `favicon.${store.format}` }}
        </button>
        <button
          id="btnPkg"
          type="button"
          class="secondary"
          :disabled="store.busy"
          @click="createPackage"
        >
          {{ t('btnPackage') }}
        </button>
      </div>
    </form>
    <StatusMessage />
    <SnippetBox />
  </div>
</template>

<style scoped>
  .buttons {
    display: flex;
    gap: var(--ds-space-3);
    margin-top: var(--ds-space-6);
  }
  @media (max-width: 480px) {
    .buttons {
      flex-direction: column;
    }
  }
</style>
