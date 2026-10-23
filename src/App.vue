<script setup lang="ts">
  import { onMounted } from 'vue'
  import { useI18n } from 'vue-i18n'
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
    <p>{{ t('intro') }}</p>

    <form id="uploadForm" @submit.prevent="createIcons">
      <ModeSwitch />
      <ImageDropzone v-show="store.mode === 'image'" />
      <TextPanel v-show="store.mode === 'text'" />
      <IconPreview />
      <FitOptions />
      <StyleOptions />

      <!-- Zwei getrennte Ausgaben: Formatwahl und Größen gelten nur für die Einzeldatei -->
      <div class="outputs">
        <section class="output" aria-labelledby="singleHeading">
          <h2 id="singleHeading">{{ t('singleHeading') }}</h2>
          <FormatOptions />
          <SizeOptions />
          <button id="btnIco" type="submit" :disabled="store.busy">
            {{ store.format === 'ico' ? 'favicon.ico' : `favicon.${store.format}` }}
          </button>
        </section>
        <section class="output" aria-labelledby="packageHeading">
          <h2 id="packageHeading">{{ t('packageHeading') }}</h2>
          <p id="packageContents" class="output-note">{{ t('packageContents') }}</p>
          <PackageOptions />
          <button
            id="btnPkg"
            type="button"
            class="secondary"
            :disabled="store.busy"
            @click="createPackage"
          >
            {{ t('btnPackage') }}
          </button>
        </section>
      </div>
    </form>
    <StatusMessage />
    <SnippetBox />
  </div>
</template>

<style scoped>
  .outputs {
    display: grid;
    gap: var(--ds-space-5);
    margin-top: var(--ds-space-6);
  }
  .output {
    display: flex;
    flex-direction: column;
    padding: var(--ds-space-4);
    border: var(--ds-border-width) solid var(--ds-border-strong);
    border-radius: var(--ds-radius-lg);
    background: var(--ds-surface-2);
    text-align: left;
  }
  .output h2 {
    margin: 0;
    font-size: var(--ds-text-md);
    font-weight: var(--ds-weight-bold);
    color: var(--ds-text);
  }
  .output-note {
    margin: var(--ds-space-2) 0 0;
    font-size: var(--ds-text-sm);
    color: var(--ds-text-2);
  }
  .output > button {
    margin-top: var(--ds-space-5);
  }
</style>
