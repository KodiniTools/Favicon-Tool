<script setup lang="ts">
  import { useI18n } from 'vue-i18n'
  import { useFaviconStore } from '@/stores/favicon'

  const { t } = useI18n()
  const store = useFaviconStore()
</script>

<template>
  <fieldset>
    <legend>{{ t('fitLegend') }}</legend>
    <div class="options">
      <label>
        <input v-model="store.fit" type="radio" name="fit" value="pad" />
        <span>{{ t('fitPad') }}</span>
      </label>
      <label>
        <input v-model="store.fit" type="radio" name="fit" value="crop" />
        <span>{{ t('fitCrop') }}</span>
      </label>
    </div>
  </fieldset>
</template>
