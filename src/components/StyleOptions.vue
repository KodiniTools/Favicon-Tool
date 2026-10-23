<script setup lang="ts">
  import { useI18n } from 'vue-i18n'
  import { useFaviconStore } from '@/stores/favicon'

  const { t } = useI18n()
  const store = useFaviconStore()
</script>

<template>
  <fieldset>
    <legend>{{ t('styleLegend') }}</legend>
    <div class="field">
      <label>
        <input id="bgEnabled" v-model="store.bgEnabled" type="checkbox" />
        <span>{{ t('bgLabel') }}</span>
      </label>
      <input
        id="bgColor"
        v-model="store.bgColor"
        type="color"
        :disabled="!store.bgEnabled"
        :aria-label="t('bgLabel')"
      />
      <span></span>
    </div>
    <div class="field">
      <label for="padding">{{ t('paddingLabel') }}</label>
      <input id="padding" v-model.number="store.padding" type="range" min="0" max="40" step="1" />
      <output id="paddingOut" for="padding">{{ store.padding }}&nbsp;%</output>
    </div>
    <div class="field">
      <label for="radius">{{ t('radiusLabel') }}</label>
      <input id="radius" v-model.number="store.radius" type="range" min="0" max="50" step="1" />
      <output id="radiusOut" for="radius">{{ store.radius }}&nbsp;%</output>
    </div>
  </fieldset>
</template>
