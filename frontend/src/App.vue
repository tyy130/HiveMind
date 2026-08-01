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
:root {
  --surface-0: #f7f9fc;
  --surface-1: #ffffff;
  --surface-2: #eef2f6;
  --ink-950: #0a1623;
  --ink-900: #132236;
  --ink-800: #24364b;
  --ink-700: #3a4e63;
  --ink-600: #52677d;
  --ink-500: #6e8194;
  --ink-400: #91a0af;
  --ink-300: #b7c1cb;
  --accent: #49deb1;
  --accent-strong: #0c9470;
  --font-display: 'Space Grotesk', 'Inter', system-ui, sans-serif;
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  min-width: 320px;
  min-height: 100vh;
  background: var(--surface-0);
}

#app {
  min-height: 100vh;
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: var(--ink-950);
  background: var(--surface-0);
}

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--surface-2);
}

::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: var(--ink-300);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--ink-500);
}

button {
  font-family: inherit;
}

button:focus-visible,
a:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible,
[role="button"]:focus-visible {
  outline: 2px solid var(--accent-strong);
  outline-offset: 2px;
}

::selection {
  color: var(--ink-950);
  background: rgba(73, 222, 177, 0.65);
}
</style>
