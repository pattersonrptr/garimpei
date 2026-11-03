/**
 * Translation resources, discovered from the folder structure:
 *
 *   src/i18n/locales/<language-code>/<namespace>.json
 *
 * Adding a language = adding a folder with the same JSON files as pt-BR.
 * Nothing here needs to change; the language switcher lists it automatically
 * (its label comes from the "languageName" key in common.json).
 */

type Messages = { [key: string]: string | Messages }

/** Source language: complete by definition, used for types and as fallback. */
export const DEFAULT_LANGUAGE = 'pt-BR'

export const NAMESPACES = [
  'common',
  'auth',
  'landing',
  'dashboard',
  'alerts',
  'products',
  'plans',
  'admin',
] as const

export type Namespace = (typeof NAMESPACES)[number]

const modules = import.meta.glob<{ default: Messages }>('./locales/*/*.json', {
  eager: true,
})

export const resources: Record<string, Record<string, Messages>> = {}

for (const [path, module] of Object.entries(modules)) {
  const match = path.match(/\.\/locales\/([^/]+)\/([^/]+)\.json$/)
  if (!match) continue
  const [, language, namespace] = match
  resources[language] ??= {}
  resources[language][namespace] = module.default
}

export interface LanguageOption {
  code: string
  name: string
}

/** Every language with translations, default language first. */
export const SUPPORTED_LANGUAGES: LanguageOption[] = Object.keys(resources)
  .sort((a, b) =>
    a === DEFAULT_LANGUAGE ? -1 : b === DEFAULT_LANGUAGE ? 1 : a.localeCompare(b),
  )
  .map((code) => ({
    code,
    name: String(resources[code].common?.languageName ?? code),
  }))
