<script setup lang="ts">
  import { useI18n } from 'vue-i18n'
  import { ALLOWED_SIZES } from '@/lib/constants'
  import { useFaviconStore } from '@/stores/favicon'

  const { t } = useI18n()
  const store = useFaviconStore()
</script>

<template>
  <fieldset>
    <legend>{{ t('sizesLegend') }}</legend>
    <div id="sizeOptions" class="options">
      <label v-for="size in ALLOWED_SIZES" :key="size">
        <input v-model="store.sizes" type="checkbox" name="size" :value="size" />
        {{ size }}
      </label>
    </div>
  </fieldset>
</template>
