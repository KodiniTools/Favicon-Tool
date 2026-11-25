<script setup lang="ts">
  import { useI18n } from 'vue-i18n'
  import { useFaviconStore } from '@/stores/favicon'

  type SliderKey = 'padding' | 'radius'

  const { t } = useI18n()
  const store = useFaviconStore()

  /** Wertebereich wie auf dem Server (parse_style): Innenabstand 0–40 %, Eckenradius 0–50 %. */
  const SLIDERS: ReadonlyArray<{
    key: SliderKey
    max: number
    label: 'paddingLabel' | 'radiusLabel'
  }> = [
    { key: 'padding', max: 40, label: 'paddingLabel' },
    { key: 'radius', max: 50, label: 'radiusLabel' },
  ]
  const DEFAULTS: Record<SliderKey, number> = { padding: 0, radius: 0 }

  /** Ganze Zahl im Bereich 0–max; ungültige Eingaben (leer, Text) liefern null. */
  function clamp(raw: string, max: number): number | null {
    if (raw.trim() === '') return null
    const n = Math.round(Number(raw))
    return Number.isFinite(n) ? Math.min(max, Math.max(0, n)) : null
  }

  /** Zahlenfeld während der Eingabe: nur gültige Werte übernehmen. */
  function onNumberInput(key: SliderKey, max: number, e: Event): void {
    const value = clamp((e.target as HTMLInputElement).value, max)
    if (value !== null) store[key] = value
  }

  /** Beim Verlassen/Bestätigen: Anzeige auf den gültigen Store-Wert zurücksetzen (z. B. leer oder 99). */
  function onNumberChange(key: SliderKey, max: number, e: Event): void {
    const input = e.target as HTMLInputElement
    const value = clamp(input.value, max)
    if (value !== null) store[key] = value
    input.value = String(store[key])
  }

  function reset(key: SliderKey): void {
    store[key] = DEFAULTS[key]
  }
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
    <div v-for="s in SLIDERS" :key="s.key" class="field slider">
      <label :for="s.key">{{ t(s.label) }}</label>
      <input :id="s.key" v-model.number="store[s.key]" type="range" min="0" :max="s.max" step="1" />
      <span class="spin">
        <input
          :id="s.key + 'Num'"
          type="number"
          inputmode="numeric"
          min="0"
          :max="s.max"
          step="1"
          :value="store[s.key]"
          :aria-label="`${t(s.label)} (%)`"
          @input="onNumberInput(s.key, s.max, $event)"
          @change="onNumberChange(s.key, s.max, $event)"
        />
        <span aria-hidden="true">%</span>
      </span>
      <button
        :id="s.key + 'Reset'"
        type="button"
        class="reset"
        :aria-label="t('resetLabel', { name: t(s.label) })"
        :title="t('resetLabel', { name: t(s.label) })"
        @click="reset(s.key)"
      >
        <span aria-hidden="true">↺</span>
        <span class="reset-text">{{ t('reset') }}</span>
      </button>
    </div>
  </fieldset>
</template>

<style scoped>
  .spin {
    display: inline-flex;
    align-items: center;
    gap: var(--ds-space-1);
    color: var(--ds-text-2);
  }
  .spin input {
    width: 4.25rem;
    min-height: var(--ds-control-md);
    padding: var(--ds-space-1) var(--ds-space-2);
    border: var(--ds-border-width) solid var(--ds-border-strong);
    border-radius: var(--ds-radius-sm);
    background: var(--ds-surface-1);
    color: var(--ds-text);
    font: inherit;
    font-size: var(--ds-text-md);
    font-variant-numeric: tabular-nums;
    text-align: right;
  }
  /* Kompakter Knopf statt der grossen App-Buttons (Farbe bleibt Dunkelgold) */
  .reset {
    flex: none;
    display: inline-flex;
    align-items: center;
    gap: var(--ds-space-1);
    min-height: var(--ds-control-md);
    padding: var(--ds-space-1) var(--ds-space-3);
    font-size: var(--ds-text-sm);
    white-space: nowrap;
  }
  /* Schmal nur das Symbol; Name bleibt über aria-label und title erhalten */
  @media (max-width: 600px) {
    .reset {
      padding-inline: var(--ds-space-2);
    }
    .reset-text {
      display: none;
    }
  }
</style>
