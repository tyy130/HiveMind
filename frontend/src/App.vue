<template>
  <router-view />
</template>

<script setup>
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'

const { locale, t } = useI18n()

watch(locale, () => {
  document.documentElement.lang = locale.value
  document.title = t('meta.title')
  document.querySelector('meta[name="description"]')?.setAttribute('content', t('meta.description'))
}, { immediate: true })
</script>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'JetBrains Mono', 'Space Grotesk', 'Noto Sans SC', monospace;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #000000;
  background-color: #ffffff;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
  background: #000000;
}

::-webkit-scrollbar-thumb:hover {
  background: #333333;
}

/* 全局按钮样式 */
button {
  font-family: inherit;
}

button:focus-visible,
a:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible,
[role="button"]:focus-visible {
  outline: 2px solid #FF4500;
  outline-offset: 2px;
}
</style>
