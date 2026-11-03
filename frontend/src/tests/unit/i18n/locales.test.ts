/**
 * Every language must mirror the source language (pt-BR): same namespaces,
 * same keys, same {{variables}}. Plural suffixes (_one, _few, _other…) are
 * compared by base key, since each language has its own plural forms.
 */

import { afterAll, describe, expect, it } from 'vitest'
import i18n from '@/i18n'
import {
  DEFAULT_LANGUAGE,
  NAMESPACES,
  resources,
  SUPPORTED_LANGUAGES,
} from '@/i18n/resources'

type Messages = { [key: string]: string | Messages }

const PLURAL_SUFFIX = /_(zero|one|two|few|many|other)$/

function flatten(messages: Messages, prefix = ''): Record<string, string> {
  return Object.entries(messages).reduce<Record<string, string>>((acc, [key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key
    if (typeof value === 'string') acc[path] = value
    else Object.assign(acc, flatten(value, path))
    return acc
  }, {})
}

/** base key -> variables used by any of its plural forms */
function shape(messages: Messages): Record<string, string[]> {
  const result: Record<string, Set<string>> = {}
  for (const [key, text] of Object.entries(flatten(messages))) {
    const base = key.replace(PLURAL_SUFFIX, '')
    result[base] ??= new Set()
    for (const match of text.matchAll(/\{\{\s*(\w+)/g)) result[base].add(match[1])
  }
  return Object.fromEntries(
    Object.entries(result).map(([key, vars]) => [key, [...vars].sort()]),
  )
}

const source = resources[DEFAULT_LANGUAGE]
const others = SUPPORTED_LANGUAGES.map((l) => l.code).filter((c) => c !== DEFAULT_LANGUAGE)

describe('locales', () => {
  it('discovers the source language and at least one translation', () => {
    expect(SUPPORTED_LANGUAGES[0].code).toBe(DEFAULT_LANGUAGE)
    expect(others.length).toBeGreaterThan(0)
  })

  it('source language has every namespace', () => {
    expect(Object.keys(source).sort()).toEqual([...NAMESPACES].sort())
  })

  describe.each(others)('%s', (language) => {
    it.each([...NAMESPACES])('%s matches the source keys and variables', (ns) => {
      const translated = resources[language][ns] as Messages | undefined
      expect(translated, `missing ${language}/${ns}.json`).toBeDefined()
      expect(shape(translated!)).toEqual(shape(source[ns] as Messages))
    })

    it('has a languageName for the switcher', () => {
      const common = flatten(resources[language].common as Messages)
      expect(common.languageName).toBeTruthy()
    })
  })
})

describe('language resolution', () => {
  // setup.ts runs the suite in English; restore it after these checks
  afterAll(() => i18n.changeLanguage('en'))

  it.each([
    ['pt-BR', 'pt-BR', 'Meus alertas'],
    ['en', 'en', 'My Alerts'],
    ['en-US', 'en', 'My Alerts'],
    ['de-DE', 'pt-BR', 'Meus alertas'], // unsupported -> default language
  ])('%s resolves to %s', async (requested, resolved, text) => {
    await i18n.changeLanguage(requested)
    expect(i18n.resolvedLanguage).toBe(resolved)
    expect(i18n.t('nav.alerts')).toBe(text)
  })
})
