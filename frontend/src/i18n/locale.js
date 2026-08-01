export const DEFAULT_LOCALE = 'zh'

export function resolveLocale(candidate, availableLocales, fallback = DEFAULT_LOCALE) {
  const localeKeys = new Set(availableLocales)

  if (localeKeys.has(candidate)) return candidate
  if (localeKeys.has(fallback)) return fallback

  return availableLocales[0]
}
