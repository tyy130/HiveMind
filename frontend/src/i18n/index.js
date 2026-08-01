import { createI18n } from 'vue-i18n'
import languages from '../../../locales/languages.json'
import { DEFAULT_LOCALE, resolveLocale } from './locale.js'

const localeFiles = import.meta.glob('../../../locales/!(languages).json', { eager: true })

const messages = {}
const availableLocales = []

for (const path in localeFiles) {
  const key = path.match(/\/([^/]+)\.json$/)[1]
  if (languages[key]) {
    messages[key] = localeFiles[path].default
    availableLocales.push({ key, label: languages[key].label })
  }
}

const savedLocale = resolveLocale(
  localStorage.getItem('locale'),
  availableLocales.map(locale => locale.key),
  DEFAULT_LOCALE
)

if (localStorage.getItem('locale') !== savedLocale) {
  localStorage.setItem('locale', savedLocale)
}

const i18n = createI18n({
  legacy: false,
  locale: savedLocale,
  fallbackLocale: DEFAULT_LOCALE,
  messages
})

export default i18n
