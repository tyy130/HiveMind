<template>
  <div class="language-switcher">
    <select
      class="switcher-trigger"
      :value="locale"
      :aria-label="$t('common.selectLanguage')"
      @change="switchLocale($event.target.value)"
    >
      <option v-for="loc in availableLocales" :key="loc.key" :value="loc.key">
        {{ loc.label }}
      </option>
    </select>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { availableLocales } from '@/i18n/index.js'

const { locale } = useI18n()

const switchLocale = (key) => {
  locale.value = key
  localStorage.setItem('locale', key)
}
</script>

<style scoped>
.language-switcher {
  position: relative;
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
}

.switcher-trigger {
  background: transparent;
  color: #333;
  border: 1px solid #CCC;
  padding: 4px 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  cursor: pointer;
  transition: border-color 0.2s, opacity 0.2s;
}

.switcher-trigger:hover {
  border-color: #999;
}

.switcher-trigger:focus-visible {
  outline: 2px solid var(--orange, #FF4500);
  outline-offset: 2px;
}
</style>
