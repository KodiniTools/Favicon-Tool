<script setup lang="ts">
  import { useI18n } from 'vue-i18n'
  import { useFaviconStore } from '@/stores/favicon'

  const { t } = useI18n()
  const store = useFaviconStore()
</script>

<template>
  <fieldset>
    <legend>{{ t('packageLegend') }}</legend>
    <div class="field stack">
      <label for="appName">{{ t('appNameLabel') }}</label>
      <input
        id="appName"
        v-model="store.appName"
        type="text"
        maxlength="60"
        :placeholder="t('appNamePlaceholder')"
      />
    </div>
    <div class="field">
      <label>
        <input id="themeEnabled" v-model="store.themeEnabled" type="checkbox" />
        <span>{{ t('themeLabel') }}</span>
      </label>
      <!-- .lazy: erst nach Abschluss der Farbwahl übernehmen (lädt das Snippet neu) -->
      <input
        id="themeColor"
        v-model.lazy="store.themeColor"
        type="color"
        :disabled="!store.themeEnabled"
        :aria-label="t('themeLabel')"
      />
      <span></span>
    </div>
  </fieldset>
</template>
