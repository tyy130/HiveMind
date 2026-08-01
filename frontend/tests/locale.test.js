import test from 'node:test'
import assert from 'node:assert/strict'

import { resolveLocale } from '../src/i18n/locale.js'

test('resolveLocale keeps supported saved locales', () => {
  assert.equal(resolveLocale('en', ['en']), 'en')
})

test('resolveLocale falls back when storage contains an unsupported locale', () => {
  assert.equal(resolveLocale('zh', ['en']), 'en')
})

test('resolveLocale uses the first loaded locale when the default is unavailable', () => {
  assert.equal(resolveLocale('fr', ['en'], 'es'), 'en')
})
