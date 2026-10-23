<script setup lang="ts">
  import { computed } from 'vue'
  import { useI18n } from 'vue-i18n'
  import FontPicker from '@/components/FontPicker.vue'
  import { fontCss, fontWeight } from '@/lib/fonts'
  import { useFaviconStore } from '@/stores/favicon'

  const { t } = useI18n()
  const store = useFaviconStore()
  // Eingabefeld in der gewählten Schrift
  const inputStyle = computed(() => ({
    fontFamily: fontCss(store.fontValue),
    fontWeight: fontWeight(store.fontValue),
  }))
</script>

<template>
  <div id="textPanel">
    <div class="field">
      <label for="iconText">{{ t('textLabel') }}</label>
      <input
        id="iconText"
        v-model="store.iconText"
        type="text"
        maxlength="4"
        autocomplete="off"
        :placeholder="t('textPlaceholder')"
        :style="inputStyle"
      />
      <span></span>
    </div>
    <div class="field">
      <label id="textFontLabel" for="textFontBtn">{{ t('fontLabel') }}</label>
      <FontPicker />
      <span></span>
    </div>
    <div class="field">
      <label for="textColor">{{ t('textColorLabel') }}</label>
      <input id="textColor" v-model="store.textColor" type="color" />
      <span></span>
    </div>
  </div>
</template>

<style scoped>
  #textPanel {
    text-align: left;
    border: 2px dashed var(--ds-border-strong);
    border-radius: var(--ds-radius-md);
    padding: var(--ds-space-4);
    background: var(--ds-surface-0);
  }
</style>
